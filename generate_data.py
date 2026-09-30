"""Erzeugt erfundene IVOM-Testdaten (Patienten, Augen, Injektionen, Bestellungen).

Simuliert grob realistische Therapieverläufe inkl. Präparatumstellungen und
absichtliche Unstimmigkeiten zwischen Bestellungen und Injektionen, damit der
Abgleich im Dashboard etwas zu finden hat.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

RNG_SEED = 42
N_PATIENTS = 200
TODAY = date(2026, 9, 26)

INDIKATIONEN = ["nAMD", "DMOe", "Venenverschluss", "sonstige"]
INDIKATION_WEIGHTS = [0.55, 0.25, 0.15, 0.05]

PRAEPARATE_START = ["Eylea 2mg", "Lucentis", "Vabysmo", "Avastin", "Biosimilar-Ranibizumab"]
UMSTELLUNG_ZIEL = {
    "Eylea 2mg": "Eylea HD (8mg)",
    "Lucentis": "Vabysmo",
    "Biosimilar-Ranibizumab": "Vabysmo",
}

random.seed(RNG_SEED)
np.random.seed(RNG_SEED)


def random_date_between(start: date, end: date) -> date:
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


def build_patients(n: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        geburtsjahr = random.randint(1935, 1965)
        geschlecht = random.choice(["m", "w"])
        rows.append({"patient_id": f"P{i:04d}", "geburtsjahr": geburtsjahr, "geschlecht": geschlecht})
    return pd.DataFrame(rows)


def build_eyes(patients: pd.DataFrame) -> pd.DataFrame:
    rows = []
    eye_counter = 1
    for _, p in patients.iterrows():
        n_eyes = 2 if random.random() < 0.4 else 1
        seiten = random.sample(["OD", "OS"], n_eyes)
        indikation = random.choices(INDIKATIONEN, weights=INDIKATION_WEIGHTS, k=1)[0]
        for seite in seiten:
            therapie_start = random_date_between(date(2021, 1, 1), date(2025, 12, 1))
            rows.append(
                {
                    "eye_id": f"E{eye_counter:04d}",
                    "patient_id": p["patient_id"],
                    "seite": seite,
                    "indikation": indikation if n_eyes == 1 or random.random() < 0.85 else random.choices(INDIKATIONEN, weights=INDIKATION_WEIGHTS, k=1)[0],
                    "therapie_start": therapie_start,
                }
            )
            eye_counter += 1
    return pd.DataFrame(rows)


def simulate_eye_injections(eye_id: str, therapie_start: date) -> tuple[list[dict], list[dict]]:
    """Simuliert Injektionstermine (Loading-Phase + Treat-and-Extend) mit
    optionaler Präparatumstellung. Gibt (injektionen, umstellungen) zurück."""

    praeparat = random.choice(PRAEPARATE_START)
    injections: list[dict] = []
    umstellungen: list[dict] = []

    current_date = therapie_start
    interval = 28  # Loading-Phase: ~4 Wochen

    switch_after = None
    if praeparat in UMSTELLUNG_ZIEL and random.random() < 0.35:
        switch_after = random.randint(3, 8)  # nach n-ter Injektion umstellen

    n_injektionen = random.randint(6, 22)
    for idx in range(n_injektionen):
        if current_date > TODAY:
            break

        visus = int(np.clip(np.random.normal(65, 10), 20, 85))
        injections.append(
            {
                "eye_id": eye_id,
                "datum": current_date,
                "praeparat": praeparat,
                "visus": visus,
            }
        )

        if switch_after is not None and idx == switch_after:
            neues_praeparat = UMSTELLUNG_ZIEL[praeparat]
            umstellungen.append(
                {
                    "eye_id": eye_id,
                    "datum": current_date,
                    "von_praeparat": praeparat,
                    "zu_praeparat": neues_praeparat,
                }
            )
            praeparat = neues_praeparat
            interval = 42  # nach Umstellung erstmal kürzeres Intervall, dann verlängern

        if idx < 3:
            interval = 28
        else:
            if switch_after is not None and idx <= switch_after + 2:
                interval = min(interval + random.randint(0, 7), 84)
            else:
                interval = min(interval + random.randint(-3, 10), 112)
            interval = max(interval, 28)
            if random.random() < 0.08:
                interval = max(28, interval - random.randint(14, 35))

        current_date = current_date + timedelta(days=interval)

    return injections, umstellungen


def build_injections_and_switches(eyes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_injections = []
    all_switches = []
    for _, e in eyes.iterrows():
        injections, switches = simulate_eye_injections(e["eye_id"], e["therapie_start"])
        all_injections.extend(injections)
        all_switches.extend(switches)

    inj_df = pd.DataFrame(all_injections)
    inj_df.insert(0, "injection_id", [f"I{i:06d}" for i in range(1, len(inj_df) + 1)])

    eye_to_patient = eyes.set_index("eye_id")["patient_id"]
    inj_df["patient_id"] = inj_df["eye_id"].map(eye_to_patient)

    switch_df = pd.DataFrame(all_switches)
    return inj_df, switch_df


def build_orders(injections: pd.DataFrame) -> pd.DataFrame:
    """Bestellungen aus Injektionen ableiten, mit absichtlichen Unstimmigkeiten:
    ~7% Injektionen ohne passende Bestellung, ~7% zusaetzliche Bestellungen ohne Injektion."""

    per_patient_praeparat_month = (
        injections.assign(monat=pd.to_datetime(injections["datum"]).values.astype("datetime64[M]"))
        .groupby(["patient_id", "praeparat", "monat"])
        .size()
        .reset_index(name="menge")
    )

    orders = []
    order_counter = 1
    for _, row in per_patient_praeparat_month.iterrows():
        if random.random() < 0.07:
            continue  # Injektion(en) ohne Bestellung -> Unstimmigkeit

        bestelldatum = pd.Timestamp(row["monat"]) + pd.Timedelta(days=random.randint(0, 5))
        orders.append(
            {
                "order_id": f"B{order_counter:05d}",
                "patient_id": row["patient_id"],
                "praeparat": row["praeparat"],
                "bestelldatum": bestelldatum.date(),
                "menge": int(row["menge"]),
            }
        )
        order_counter += 1

    # zusaetzliche Bestellungen ohne zugehoerige Injektion (z.B. Vorrat, Stornierung nicht erfasst)
    n_extra = max(1, int(len(orders) * 0.05))
    sample_patients = injections["patient_id"].drop_duplicates().sample(n_extra, random_state=RNG_SEED)
    for patient_id in sample_patients:
        praeparat = random.choice(PRAEPARATE_START + list(UMSTELLUNG_ZIEL.values()))
        bestelldatum = random_date_between(date(2024, 1, 1), TODAY)
        orders.append(
            {
                "order_id": f"B{order_counter:05d}",
                "patient_id": patient_id,
                "praeparat": praeparat,
                "bestelldatum": bestelldatum,
                "menge": 1,
            }
        )
        order_counter += 1

    orders_df = pd.DataFrame(orders).sort_values("bestelldatum").reset_index(drop=True)
    return orders_df


def main() -> None:
    patients = build_patients(N_PATIENTS)
    eyes = build_eyes(patients)
    injections, switches = build_injections_and_switches(eyes)
    orders = build_orders(injections)

    out_dir = "data"
    import os

    os.makedirs(out_dir, exist_ok=True)
    patients.to_csv(f"{out_dir}/patients.csv", index=False)
    eyes.to_csv(f"{out_dir}/eyes.csv", index=False)
    injections.to_csv(f"{out_dir}/injections.csv", index=False)
    switches.to_csv(f"{out_dir}/switches.csv", index=False)
    orders.to_csv(f"{out_dir}/orders.csv", index=False)

    print(f"Patienten:    {len(patients)}")
    print(f"Augen:        {len(eyes)}")
    print(f"Injektionen:  {len(injections)}")
    print(f"Umstellungen: {len(switches)}")
    print(f"Bestellungen: {len(orders)}")


if __name__ == "__main__":
    main()
