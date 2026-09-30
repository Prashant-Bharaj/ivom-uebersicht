"""Natural language → structured IVOM filters via GMA v2 completion."""

from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from lib import mga

FILTER_SCHEMA_KEYS = (
    "indikationen",
    "praeparate",
    "seiten",
    "datum_von",
    "datum_bis",
    "nur_mit_umstellung",
    "von_praeparat",
    "zu_praeparat",
    "erklaerung",
)

SYSTEM_PROMPT = """Du wandelst deutsche Anfragen zu IVOM-Datenfiltern in JSON um.
Antworte NUR mit einem JSON-Objekt (kein Markdown, keine Erklaerung ausserhalb von JSON).

Schema:
{
  "indikationen": string[] | null,
  "praeparate": string[] | null,
  "seiten": string[] | null,
  "datum_von": "YYYY-MM-DD" | null,
  "datum_bis": "YYYY-MM-DD" | null,
  "nur_mit_umstellung": boolean,
  "von_praeparat": string | null,
  "zu_praeparat": string | null,
  "erklaerung": string
}

Regeln:
- null oder leeres Array = keine Einschraenkung fuer dieses Feld.
- Verwende NUR Werte aus dem bereitgestellten Katalog (exakte Schreibweise).
- seiten nur "OD" oder "OS".
- nur_mit_umstellung=true wenn der Nutzer Umstellungen/Switch/Wechsel meint.
- von_praeparat/zu_praeparat nur setzen wenn Richtung der Umstellung genannt wird.
- erklaerung: ein kurzer deutscher Satz was gefiltert wird.
- Bei unklarer Anfrage: moeglichst wenig einschraenken und das in erklaerung sagen.
"""


def empty_filters() -> dict[str, Any]:
    return {
        "indikationen": None,
        "praeparate": None,
        "seiten": None,
        "datum_von": None,
        "datum_bis": None,
        "nur_mit_umstellung": False,
        "von_praeparat": None,
        "zu_praeparat": None,
        "erklaerung": "",
    }


def catalog_from_data(
    eyes: pd.DataFrame,
    injections: pd.DataFrame,
    switches: pd.DataFrame,
) -> dict[str, list[str]]:
    return {
        "indikationen": sorted(eyes["indikation"].dropna().unique().tolist()),
        "praeparate": sorted(injections["praeparat"].dropna().unique().tolist()),
        "seiten": sorted(eyes["seite"].dropna().unique().tolist()),
        "von_praeparate": sorted(switches["von_praeparat"].dropna().unique().tolist()),
        "zu_praeparate": sorted(switches["zu_praeparat"].dropna().unique().tolist()),
    }


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("Modellantwort enthaelt kein JSON-Objekt") from None
        return json.loads(match.group(0))


def _normalize_list(value: Any, allowed: list[str] | None = None) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return None
    items = [str(v).strip() for v in value if v is not None and str(v).strip()]
    if allowed is not None:
        allowed_set = set(allowed)
        items = [v for v in items if v in allowed_set]
    return items or None


def sanitize_filters(raw: dict[str, Any], catalog: dict[str, list[str]]) -> dict[str, Any]:
    out = empty_filters()
    out["indikationen"] = _normalize_list(raw.get("indikationen"), catalog["indikationen"])
    out["praeparate"] = _normalize_list(raw.get("praeparate"), catalog["praeparate"])
    out["seiten"] = _normalize_list(raw.get("seiten"), catalog["seiten"])
    out["von_praeparat"] = None
    out["zu_praeparat"] = None

    von = raw.get("von_praeparat")
    zu = raw.get("zu_praeparat")
    if isinstance(von, str) and von in catalog["praeparate"]:
        out["von_praeparat"] = von
    if isinstance(zu, str) and zu in catalog["praeparate"]:
        out["zu_praeparat"] = zu

    for key in ("datum_von", "datum_bis"):
        val = raw.get(key)
        if isinstance(val, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", val.strip()):
            out[key] = val.strip()

    out["nur_mit_umstellung"] = bool(raw.get("nur_mit_umstellung")) or bool(
        out["von_praeparat"] or out["zu_praeparat"]
    )
    erkl = raw.get("erklaerung")
    out["erklaerung"] = str(erkl).strip() if erkl else "Filter aus Anfrage abgeleitet."
    return out


def parse_nl_query(query: str, catalog: dict[str, list[str]], *, model: str | None = None) -> dict[str, Any]:
    user = (
        f"Katalog:\n{json.dumps(catalog, ensure_ascii=False, indent=2)}\n\n"
        f"Anfrage:\n{query.strip()}"
    )
    content = mga.chat_completion(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        model=model,
        max_tokens=512,
        temperature=0.0,
    )
    raw = _extract_json(content)
    if not isinstance(raw, dict):
        raise ValueError("Erwartetes JSON-Objekt vom Modell")
    return sanitize_filters(raw, catalog)


def apply_filters(
    filters: dict[str, Any],
    *,
    eyes: pd.DataFrame,
    injections: pd.DataFrame,
    orders: pd.DataFrame,
    switches: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Wendet strukturierte Filter auf die Rohdaten an."""

    eyes_f = eyes.copy()
    injections_f = injections.copy()
    switches_f = switches.copy()
    orders_f = orders.copy()

    if filters.get("indikationen"):
        eyes_f = eyes_f[eyes_f["indikation"].isin(filters["indikationen"])]
    if filters.get("seiten"):
        eyes_f = eyes_f[eyes_f["seite"].isin(filters["seiten"])]

    eye_ids = set(eyes_f["eye_id"])
    injections_f = injections_f[injections_f["eye_id"].isin(eye_ids)]
    switches_f = switches_f[switches_f["eye_id"].isin(eye_ids)]

    if filters.get("praeparate"):
        injections_f = injections_f[injections_f["praeparat"].isin(filters["praeparate"])]

    if filters.get("datum_von"):
        von = pd.Timestamp(filters["datum_von"])
        injections_f = injections_f[injections_f["datum"] >= von]
        switches_f = switches_f[switches_f["datum"] >= von]
    if filters.get("datum_bis"):
        bis = pd.Timestamp(filters["datum_bis"])
        injections_f = injections_f[injections_f["datum"] <= bis]
        switches_f = switches_f[switches_f["datum"] <= bis]

    if filters.get("nur_mit_umstellung") or filters.get("von_praeparat") or filters.get("zu_praeparat"):
        sw = switches_f
        if filters.get("von_praeparat"):
            sw = sw[sw["von_praeparat"] == filters["von_praeparat"]]
        if filters.get("zu_praeparat"):
            sw = sw[sw["zu_praeparat"] == filters["zu_praeparat"]]
        switch_eyes = set(sw["eye_id"])
        eyes_f = eyes_f[eyes_f["eye_id"].isin(switch_eyes)]
        eye_ids = set(eyes_f["eye_id"])
        injections_f = injections_f[injections_f["eye_id"].isin(eye_ids)]
        switches_f = sw[sw["eye_id"].isin(eye_ids)]

    # Wenn Praeparat/Zeitfilter Augen ohne passende Injektionen leer lassen wuerde,
    # Augen auf jene mit verbleibenden Injektionen beschraenken (ausser reiner Umstellungsfilter).
    if filters.get("praeparate") or filters.get("datum_von") or filters.get("datum_bis"):
        inj_eyes = set(injections_f["eye_id"])
        eyes_f = eyes_f[eyes_f["eye_id"].isin(inj_eyes)]
        eye_ids = set(eyes_f["eye_id"])
        switches_f = switches_f[switches_f["eye_id"].isin(eye_ids)]

    patient_ids = set(eyes_f["patient_id"])
    orders_f = orders_f[orders_f["patient_id"].isin(patient_ids)]
    if filters.get("praeparate"):
        orders_f = orders_f[orders_f["praeparat"].isin(filters["praeparate"])]
    if filters.get("datum_von"):
        orders_f = orders_f[orders_f["bestelldatum"] >= pd.Timestamp(filters["datum_von"])]
    if filters.get("datum_bis"):
        orders_f = orders_f[orders_f["bestelldatum"] <= pd.Timestamp(filters["datum_bis"])]

    return {
        "eyes": eyes_f,
        "injections": injections_f,
        "orders": orders_f,
        "switches": switches_f,
    }


def filters_active(filters: dict[str, Any] | None) -> bool:
    if not filters:
        return False
    return any(
        [
            filters.get("indikationen"),
            filters.get("praeparate"),
            filters.get("seiten"),
            filters.get("datum_von"),
            filters.get("datum_bis"),
            filters.get("nur_mit_umstellung"),
            filters.get("von_praeparat"),
            filters.get("zu_praeparat"),
        ]
    )
