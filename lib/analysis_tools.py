"""Analyse-Tools fuer den Datenanalyse-Chat: jede Funktion berechnet echte
Kennzahlen aus den (ungefilterten) IVOM-Testdaten via pandas. GMA v2 ruft diese
Tools per Function-Calling auf, damit Antworten auf echten Zahlen basieren
statt auf vom Modell erfundenen Werten."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from lib import metrics as lm


def _as_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return None


def _filter_eyes(eyes: pd.DataFrame, indikation=None, seite=None) -> pd.DataFrame:
    df = eyes
    ind = _as_list(indikation)
    sei = _as_list(seite)
    if ind:
        df = df[df["indikation"].isin(ind)]
    if sei:
        df = df[df["seite"].isin(sei)]
    return df


def cohort_uebersicht(data: dict[str, pd.DataFrame], indikation=None) -> dict:
    """Anzahl Patienten/Augen, aufgeschluesselt nach Indikation (optional gefiltert)."""

    eyes = _filter_eyes(data["eyes"], indikation=indikation)
    je_indikation = eyes.groupby("indikation").agg(
        anzahl_augen=("eye_id", "nunique"), anzahl_patienten=("patient_id", "nunique")
    )
    return {
        "anzahl_patienten_gesamt": int(eyes["patient_id"].nunique()),
        "anzahl_augen_gesamt": int(eyes["eye_id"].nunique()),
        "je_indikation": je_indikation.reset_index().to_dict(orient="records"),
    }


def intervall_statistik(data: dict[str, pd.DataFrame], indikation=None, praeparat=None) -> dict:
    """Statistik (Mittelwert, Median, Min, Max, n) der Intervalllaengen in Tagen,
    optional gefiltert nach Indikation und/oder Praeparat."""

    eyes = _filter_eyes(data["eyes"], indikation=indikation)
    injections = data["injections"][data["injections"]["eye_id"].isin(eyes["eye_id"])]
    intervals = lm.compute_intervals(injections).dropna(subset=["intervall_tage"])

    praep = _as_list(praeparat)
    if praep:
        intervals = intervals[intervals["praeparat"].isin(praep)]

    if intervals.empty:
        return {"n": 0, "hinweis": "Keine Intervalle fuer diese Auswahl gefunden."}

    s = intervals["intervall_tage"]
    return {
        "n": int(s.shape[0]),
        "anzahl_augen": int(intervals["eye_id"].nunique()),
        "mittelwert_tage": round(float(s.mean()), 1),
        "median_tage": round(float(s.median()), 1),
        "min_tage": int(s.min()),
        "max_tage": int(s.max()),
        "std_tage": round(float(s.std()), 1) if s.shape[0] > 1 else 0.0,
    }


def injektionen_pro_jahr(data: dict[str, pd.DataFrame], indikation=None) -> dict:
    """Mittlere Injektionsanzahl pro Auge und Therapiejahr, optional gefiltert nach Indikation."""

    eyes = _filter_eyes(data["eyes"], indikation=indikation)
    injections = data["injections"][data["injections"]["eye_id"].isin(eyes["eye_id"])]
    mit_jahr = lm.add_relative_time(injections, eyes)
    tab = lm.injektionen_pro_therapiejahr(mit_jahr)
    return {"pro_therapiejahr": tab.to_dict(orient="records")}


def praeparatumstellung_effekt(data: dict[str, pd.DataFrame], von_praeparat=None, zu_praeparat=None) -> dict:
    """Mittlere Intervalllaenge vor/nach Praeparatumstellung, optional gefiltert
    nach Ausgangs- und/oder Zielpraeparat."""

    switches = data["switches"]
    if von_praeparat:
        switches = switches[switches["von_praeparat"] == von_praeparat]
    if zu_praeparat:
        switches = switches[switches["zu_praeparat"] == zu_praeparat]

    if switches.empty:
        return {"n": 0, "hinweis": "Keine Umstellungen fuer diese Auswahl gefunden."}

    intervals = lm.compute_intervals(data["injections"])
    verlaengerung = lm.intervall_verlaengerung_nach_umstellung(intervals, switches)
    if verlaengerung.empty:
        return {"n": 0, "hinweis": "Keine auswertbaren Umstellungen (zu wenige Injektionen davor/danach)."}

    zusammenfassung = (
        verlaengerung.groupby(["von_praeparat", "zu_praeparat"])
        .agg(
            faelle=("eye_id", "count"),
            intervall_vor_tage=("intervall_vor_tage", "mean"),
            intervall_nach_tage=("intervall_nach_tage", "mean"),
            veraenderung_tage=("veraenderung_tage", "mean"),
        )
        .round(1)
        .reset_index()
    )
    return {"umstellungen": zusammenfassung.to_dict(orient="records")}


def bestellungen_abgleich_statistik(data: dict[str, pd.DataFrame], indikation=None) -> dict:
    """Anzahl und Art der Unstimmigkeiten zwischen Bestellungen und Injektionen,
    optional gefiltert nach Indikation."""

    eyes = _filter_eyes(data["eyes"], indikation=indikation)
    patient_ids = set(eyes["patient_id"])
    injections = data["injections"][data["injections"]["patient_id"].isin(patient_ids)]
    orders = data["orders"][data["orders"]["patient_id"].isin(patient_ids)]

    abgleich = lm.abgleich_bestellungen_injektionen(orders, injections)
    status_counts = abgleich["status"].value_counts().to_dict()
    return {
        "datensaetze_geprueft": int(abgleich.shape[0]),
        "unstimmigkeiten_gesamt": int((abgleich["status"] != "OK").sum()),
        "nach_status": status_counts,
    }


def praeparat_verteilung(data: dict[str, pd.DataFrame], indikation=None) -> dict:
    """Anzahl Injektionen je Praeparat, optional gefiltert nach Indikation."""

    eyes = _filter_eyes(data["eyes"], indikation=indikation)
    injections = data["injections"][data["injections"]["eye_id"].isin(eyes["eye_id"])]
    counts = injections["praeparat"].value_counts().to_dict()
    return {"anzahl_injektionen_je_praeparat": counts, "gesamt": int(injections.shape[0])}


def patient_suche(data: dict[str, pd.DataFrame], patient_id: str) -> dict:
    """Details zu einem einzelnen Patienten: Augen, Injektionen, Umstellungen."""

    eyes = data["eyes"][data["eyes"]["patient_id"] == patient_id]
    if eyes.empty:
        return {"gefunden": False, "hinweis": f"Patient {patient_id} nicht gefunden."}

    injections = data["injections"][data["injections"]["patient_id"] == patient_id].merge(
        eyes[["eye_id", "seite"]], on="eye_id", how="left"
    )
    switches = data["switches"][data["switches"]["eye_id"].isin(eyes["eye_id"])]

    return {
        "gefunden": True,
        "patient_id": patient_id,
        "augen": eyes[["eye_id", "seite", "indikation", "therapie_start"]].assign(
            therapie_start=lambda d: d["therapie_start"].dt.date.astype(str)
        ).to_dict(orient="records"),
        "anzahl_injektionen": int(injections.shape[0]),
        "injektionen": injections[["datum", "seite", "praeparat", "visus"]]
        .assign(datum=lambda d: d["datum"].dt.date.astype(str))
        .sort_values("datum")
        .to_dict(orient="records"),
        "umstellungen": switches.assign(datum=lambda d: d["datum"].dt.date.astype(str)).to_dict(orient="records")
        if not switches.empty
        else [],
    }


def verfuegbare_werte(data: dict[str, pd.DataFrame]) -> dict:
    """Gueltige Werte fuer Indikation, Praeparat, Auge — zur Orientierung vor anderen Tool-Aufrufen."""

    return {
        "indikationen": sorted(data["eyes"]["indikation"].dropna().unique().tolist()),
        "praeparate": sorted(data["injections"]["praeparat"].dropna().unique().tolist()),
        "seiten": sorted(data["eyes"]["seite"].dropna().unique().tolist()),
    }


TOOL_FUNCS: dict[str, Callable[..., dict]] = {
    "cohort_uebersicht": cohort_uebersicht,
    "intervall_statistik": intervall_statistik,
    "injektionen_pro_jahr": injektionen_pro_jahr,
    "praeparatumstellung_effekt": praeparatumstellung_effekt,
    "bestellungen_abgleich_statistik": bestellungen_abgleich_statistik,
    "praeparat_verteilung": praeparat_verteilung,
    "patient_suche": patient_suche,
    "verfuegbare_werte": verfuegbare_werte,
}

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "cohort_uebersicht",
            "description": "Anzahl Patienten und Augen, aufgeschluesselt nach Indikation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indikation": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: nur diese Indikation(en) beruecksichtigen.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "intervall_statistik",
            "description": "Statistik (Mittelwert, Median, Min, Max, n) der Intervalllaengen zwischen Injektionen in Tagen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indikation": {"type": "array", "items": {"type": "string"}},
                    "praeparat": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "injektionen_pro_jahr",
            "description": "Mittlere Injektionsanzahl pro Auge und Therapiejahr (1, 2, 3, ...), z. B. um zu zeigen dass Jahr 1 mehr Injektionen braucht als spaetere Jahre.",
            "parameters": {
                "type": "object",
                "properties": {"indikation": {"type": "array", "items": {"type": "string"}}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "praeparatumstellung_effekt",
            "description": "Mittlere Intervalllaenge vor/nach Praeparatumstellung (z. B. Eylea 2mg -> Eylea HD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "von_praeparat": {"type": "string"},
                    "zu_praeparat": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bestellungen_abgleich_statistik",
            "description": "Anzahl und Art der Unstimmigkeiten zwischen Bestellungen (Medios-Apotheke) und tatsaechlichen Injektionen.",
            "parameters": {
                "type": "object",
                "properties": {"indikation": {"type": "array", "items": {"type": "string"}}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "praeparat_verteilung",
            "description": "Anzahl Injektionen je Praeparat (Praeparatemix).",
            "parameters": {
                "type": "object",
                "properties": {"indikation": {"type": "array", "items": {"type": "string"}}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patient_suche",
            "description": "Details zu einem einzelnen Patienten anhand der Patienten-ID (z. B. 'P0010'): Augen, alle Injektionen, Umstellungen.",
            "parameters": {
                "type": "object",
                "properties": {"patient_id": {"type": "string"}},
                "required": ["patient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verfuegbare_werte",
            "description": "Gueltige Werte fuer Indikation, Praeparat und Auge-Seite. Vor anderen Tool-Aufrufen nutzen, wenn unsicher ist wie ein Begriff genau geschrieben wird.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def execute_tool(name: str, arguments: dict, data: dict[str, pd.DataFrame]) -> dict:
    func = TOOL_FUNCS.get(name)
    if func is None:
        return {"fehler": f"Unbekanntes Tool: {name}"}
    try:
        return func(data, **arguments)
    except Exception as exc:  # noqa: BLE001 — Fehler als Tool-Ergebnis zurueckgeben statt Crash
        return {"fehler": str(exc)}
