"""Laden und Verknuepfen der rohen CSV-Exporte zu sauberen DataFrames."""

from __future__ import annotations

import pandas as pd

DATA_DIR = "data"


def load_patients() -> pd.DataFrame:
    return pd.read_csv(f"{DATA_DIR}/patients.csv")


def load_eyes() -> pd.DataFrame:
    return pd.read_csv(f"{DATA_DIR}/eyes.csv", parse_dates=["therapie_start"])


def load_injections() -> pd.DataFrame:
    return pd.read_csv(f"{DATA_DIR}/injections.csv", parse_dates=["datum"])


def load_switches() -> pd.DataFrame:
    return pd.read_csv(f"{DATA_DIR}/switches.csv", parse_dates=["datum"])


def load_orders() -> pd.DataFrame:
    return pd.read_csv(f"{DATA_DIR}/orders.csv", parse_dates=["bestelldatum"])


def load_all() -> dict[str, pd.DataFrame]:
    return {
        "patients": load_patients(),
        "eyes": load_eyes(),
        "injections": load_injections(),
        "switches": load_switches(),
        "orders": load_orders(),
    }


def eyes_in_therapie(eyes: pd.DataFrame, injections: pd.DataFrame, stichtag: pd.Timestamp, aktiv_tage: int = 180) -> pd.DataFrame:
    """Augen mit mindestens einer Injektion innerhalb der letzten `aktiv_tage` vor Stichtag."""

    letzte_inj = injections.groupby("eye_id")["datum"].max().rename("letzte_injektion")
    merged = eyes.merge(letzte_inj, on="eye_id", how="left")
    schwelle = stichtag - pd.Timedelta(days=aktiv_tage)
    merged["in_therapie"] = merged["letzte_injektion"] >= schwelle
    return merged
