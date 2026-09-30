"""Berechnungen fuer die IVOM-Uebersicht: Intervalllaengen, Praeparatemix,
Therapieverlaeufe und Abgleich Bestellungen <-> Injektionen."""

from __future__ import annotations

import pandas as pd


def compute_intervals(injections: pd.DataFrame) -> pd.DataFrame:
    """Intervall (Tage) zwischen aufeinanderfolgenden Injektionen je Auge."""

    df = injections.sort_values(["eye_id", "datum"]).copy()
    df["intervall_tage"] = df.groupby("eye_id")["datum"].diff().dt.days
    df["vorheriges_praeparat"] = df.groupby("eye_id")["praeparat"].shift()
    df["praeparat_gewechselt"] = df["praeparat"] != df["vorheriges_praeparat"]
    return df


def mark_phase(injections: pd.DataFrame, loading_n: int = 3) -> pd.DataFrame:
    """Markiert je Auge die ersten `loading_n` Injektionen als Loading-Phase,
    den Rest als Erhaltungsphase (Treat-and-Extend)."""

    df = injections.sort_values(["eye_id", "datum"]).copy()
    df["injektions_nr"] = df.groupby("eye_id").cumcount() + 1
    df["phase"] = df["injektions_nr"].apply(
        lambda n: "Loading-Phase" if n <= loading_n else "Erhaltung (Treat-and-Extend)"
    )
    return df


def add_relative_time(injections: pd.DataFrame, eyes: pd.DataFrame) -> pd.DataFrame:
    """Fuegt Tage seit Therapiestart und Therapiejahr (bezogen auf eyes.therapie_start) hinzu."""

    df = injections.merge(
        eyes[["eye_id", "seite", "indikation", "therapie_start"]], on="eye_id", how="left"
    )
    df["tage_seit_start"] = (df["datum"] - df["therapie_start"]).dt.days
    df["therapiejahr"] = (df["tage_seit_start"] // 365) + 1
    return df


def injektionen_pro_therapiejahr(injections_mit_jahr: pd.DataFrame, max_jahr: int = 5) -> pd.DataFrame:
    """Mittlere Injektionsanzahl pro Auge und Therapiejahr, gruppiert nach Indikation.
    Jahre >= max_jahr werden zusammengefasst (kleinere Fallzahl in Spaetjahren)."""

    d = injections_mit_jahr.copy()
    d["therapiejahr_sort"] = d["therapiejahr"].clip(upper=max_jahr).astype(int)
    d["therapiejahr_label"] = d["therapiejahr_sort"].apply(
        lambda j: f"Jahr {j}" if j < max_jahr else f"Jahr {max_jahr}+"
    )

    pro_auge_jahr = (
        d.groupby(["indikation", "eye_id", "therapiejahr_sort", "therapiejahr_label"])
        .size()
        .reset_index(name="injektionen")
    )
    zusammenfassung = (
        pro_auge_jahr.groupby(["indikation", "therapiejahr_sort", "therapiejahr_label"])
        .agg(mittlere_injektionen=("injektionen", "mean"), anzahl_augen=("eye_id", "nunique"))
        .reset_index()
        .sort_values(["indikation", "therapiejahr_sort"])
    )
    zusammenfassung["mittlere_injektionen"] = zusammenfassung["mittlere_injektionen"].round(2)
    return zusammenfassung


def medikamenten_mix_monatlich(injections: pd.DataFrame) -> pd.DataFrame:
    """Anzahl Injektionen pro Praeparat und Monat."""

    df = injections.copy()
    df["monat"] = df["datum"].values.astype("datetime64[M]")
    mix = df.groupby(["monat", "praeparat"]).size().reset_index(name="anzahl")
    return mix


def intervall_uebersicht(intervals: pd.DataFrame, eyes: pd.DataFrame) -> pd.DataFrame:
    """Intervalle je Patient/Auge/Praeparat mit Indikation angereichert, ohne
    den ersten (Loading-)Eintrag pro Auge, der kein Intervall hat."""

    df = intervals.dropna(subset=["intervall_tage"]).copy()
    df = df.merge(eyes[["eye_id", "seite", "indikation"]], on="eye_id", how="left")
    return df[["patient_id", "eye_id", "seite", "indikation", "praeparat", "datum", "intervall_tage", "praeparat_gewechselt"]]


def intervall_verlaengerung_nach_umstellung(intervals: pd.DataFrame, switches: pd.DataFrame) -> pd.DataFrame:
    """Fuer jede Umstellung: mittleres Intervall davor vs. danach (gleiche Anzahl Injektionen)."""

    ergebnisse = []
    for _, sw in switches.iterrows():
        eye_id = sw["eye_id"]
        eye_intervals = intervals[intervals["eye_id"] == eye_id].dropna(subset=["intervall_tage"])
        vor = eye_intervals[eye_intervals["datum"] <= sw["datum"]]["intervall_tage"]
        nach = eye_intervals[eye_intervals["datum"] > sw["datum"]]["intervall_tage"]
        if len(vor) == 0 or len(nach) == 0:
            continue
        ergebnisse.append(
            {
                "eye_id": eye_id,
                "von_praeparat": sw["von_praeparat"],
                "zu_praeparat": sw["zu_praeparat"],
                "intervall_vor_tage": round(vor.mean(), 1),
                "intervall_nach_tage": round(nach.mean(), 1),
                "veraenderung_tage": round(nach.mean() - vor.mean(), 1),
            }
        )
    return pd.DataFrame(ergebnisse)


def abgleich_bestellungen_injektionen(orders: pd.DataFrame, injections: pd.DataFrame) -> pd.DataFrame:
    """Vergleicht Bestellmenge vs. Injektionsanzahl je Patient/Praeparat/Monat
    und markiert Unstimmigkeiten."""

    inj = injections.copy()
    inj["monat"] = inj["datum"].values.astype("datetime64[M]")
    inj_agg = inj.groupby(["patient_id", "praeparat", "monat"]).size().reset_index(name="injektionen")

    ord_df = orders.copy()
    ord_df["monat"] = ord_df["bestelldatum"].values.astype("datetime64[M]")
    ord_agg = ord_df.groupby(["patient_id", "praeparat", "monat"])["menge"].sum().reset_index(name="bestellt")

    merged = pd.merge(inj_agg, ord_agg, on=["patient_id", "praeparat", "monat"], how="outer")
    merged["injektionen"] = merged["injektionen"].fillna(0).astype(int)
    merged["bestellt"] = merged["bestellt"].fillna(0).astype(int)
    merged["differenz"] = merged["bestellt"] - merged["injektionen"]
    merged["unstimmigkeit"] = merged["differenz"] != 0

    def _label(row):
        if row["differenz"] > 0:
            return "Bestellung ohne Injektion"
        if row["differenz"] < 0:
            return "Injektion ohne Bestellung"
        return "OK"

    merged["status"] = merged.apply(_label, axis=1)
    return merged.sort_values(["patient_id", "monat"])
