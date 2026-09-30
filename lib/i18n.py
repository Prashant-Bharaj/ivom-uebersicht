"""Minimalistische UI-Uebersetzung (Deutsch/Englisch) fuer die IVOM-Uebersicht."""

from __future__ import annotations

import pandas as pd

DEFAULT_LANG = "de"

LANGUAGES = {"de": "Deutsch", "en": "English"}

STRINGS: dict[str, dict[str, str]] = {
    "de": {
        "app_title": "IVOM-Uebersicht",
        "app_caption": "Prototyp mit erfundenen Testdaten · vertraulich · nur zur Entwicklung",
        "language_label": "Sprache",
        "sidebar_filter_header": "Filter",
        "nl_subheader": "Natuerliche Sprache",
        "nl_caption": "GMA v2 · z. B. „nAMD mit Umstellung Eylea 2mg auf HD seit 2024“",
        "nl_placeholder": "Augen mit Intervallverlaengerung nach Umstellung auf Vabysmo…",
        "btn_apply": "Anwenden",
        "btn_reset": "Zuruecksetzen",
        "err_empty_query": "Bitte eine Filterbeschreibung eingeben.",
        "nl_spinner": "Filter wird mit GMA v2 interpretiert…",
        "nl_active_default": "NL-Filter aktiv",
        "nl_json_expander": "Strukturierter Filter (JSON)",
        "mga_model_label": "Modell (GMA v2)",
        "mga_test_button": "Verbindung testen",
        "mga_test_spinner": "Teste Verbindung zu {model}…",
        "mga_test_success": "Verbunden mit **{model}** ({dauer}s) · Antwort: „{antwort}“",
        "mga_test_error": "Verbindung zu {model} fehlgeschlagen: {fehler}",
        "indikation_label": "Indikation",
        "header_1": "Patienten und Augen in Therapie",
        "metric_eyes_therapy": "Augen in Therapie",
        "metric_patients_therapy": "Patienten in Therapie",
        "metric_eyes_total": "Augen gesamt (Filter)",
        "metric_stichtag": "Stichtag",
        "chart_indikation_x": "Indikation",
        "chart_indikation_y": "Augen in Therapie",
        "header_2": "Praeparate und Praeparatemix im Zeitverlauf",
        "info_no_injections_filter": "Keine Injektionen im aktuellen Filter.",
        "checkbox_normalize": "Anteile normieren (100%)",
        "chart_mix_x": "Monat",
        "chart_mix_y": "Injektionen",
        "chart_mix_color": "Praeparat",
        "header_3": "Intervalllaengen je Patient, Auge und Praeparat",
        "sub_dist_by_med": "Verteilung nach Praeparat",
        "info_no_intervals": "Keine Intervalle im aktuellen Filter.",
        "box_x": "Praeparat",
        "box_y": "Intervall (Tage)",
        "sub_extension_after_switch": "Intervallverlaengerung nach Praeparatumstellung",
        "info_no_switches": "Keine Umstellungen im aktuellen Filter.",
        "caption_example_switch": "Beispiel: Eylea 2mg → Eylea HD (8mg) zeigt die mittlere Intervallveraenderung in Tagen.",
        "expander_all_intervals": "Alle Intervalle als Tabelle",
        "header_4": "Therapieverlaeufe",
        "info_no_patients": "Keine Patienten im aktuellen Filter.",
        "select_patient_label": "Patient auswaehlen",
        "info_no_injections_patient": "Keine Injektionen fuer diesen Patienten im aktuellen Filter.",
        "caption_patient_info": "**{patient}** · Auge(n): {augen} · Indikation: {indikation}",
        "timeline_x": "Datum",
        "timeline_y": "Auge",
        "timeline_color": "Praeparat",
        "timeline_shape": "Phase",
        "visus_y": "Visus (ETDRS)",
        "visus_color": "Auge",
        "label_switches_bold": "**Praeparatumstellungen:**",
        "expander_all_injections": "Alle Injektionen dieses Patienten",
        "header_5": "Abgleich Bestellungen gegen Injektionen",
        "metric_discrepancies": "Unstimmigkeiten gesamt",
        "metric_records_checked": "Datensaetze geprueft",
        "checkbox_only_discrepancies": "Nur Unstimmigkeiten anzeigen",
        "sub_therapy_year": "Injektionen pro Therapiejahr (nach Indikation)",
        "info_no_year_data": "Keine Daten fuer die Therapiejahr-Auswertung im aktuellen Filter.",
        "chart_year_x": "Therapiejahr",
        "chart_year_y": "Injektionen pro Auge (Mittelwert)",
        "caption_year_note": (
            "Erwartungsgemaess hoehere Injektionslast im 1. Jahr (Loading-Phase), danach abnehmend. "
            "Spaetere Jahre basieren auf weniger Augen (kuerzere Nachbeobachtung) — vorsichtig interpretieren."
        ),
        "sub_all_patients_overview": "Uebersicht aller Patienten im aktuellen Filter ({count})",
        "caption_grid_note_truncated": (
            "Zeige {shown} von {total} Patienten. "
            "Farbwechsel innerhalb einer Kachel = Praeparatumstellung. Details unten einzeln auswaehlen."
        ),
        "caption_grid_note": "Farbwechsel innerhalb einer Kachel = Praeparatumstellung. Details unten einzeln auswaehlen.",
        "label_interval_by_eye": "**Intervallverlauf je Auge:**",
        "radio_all_eyes": "Alle Augen",
        "info_no_intervals_patient": "Noch keine Intervalle (mind. 2 Injektionen je Auge erforderlich).",
        "chat_header": "Datenanalyse-Chat",
        "chat_caption": (
            "Fragen in natuerlicher Sprache an den gesamten Datensatz (unabhaengig von den Filtern oben). "
            "GMA v2 ruft echte Berechnungen ab, bevor es antwortet."
        ),
        "chat_placeholder": "z. B. Wie viele Injektionen brauchen DMOe-Patienten im 1. vs. 3. Jahr im Schnitt?",
        "chat_clear_button": "Chat zuruecksetzen",
        "chat_thinking": "Werte Daten aus…",
        "chat_tool_calls_expander": "Aufgerufene Berechnungen ({count})",
        "chat_error": "Fehler bei der Analyse: {fehler}",
    },
    "en": {
        "app_title": "IVOM Overview",
        "app_caption": "Prototype with fictitious test data · confidential · for development only",
        "language_label": "Language",
        "sidebar_filter_header": "Filters",
        "nl_subheader": "Natural language",
        "nl_caption": "GMA v2 · e.g. “nAMD with switch Eylea 2mg to HD since 2024”",
        "nl_placeholder": "Eyes with interval extension after switching to Vabysmo…",
        "btn_apply": "Apply",
        "btn_reset": "Reset",
        "err_empty_query": "Please enter a filter description.",
        "nl_spinner": "Interpreting filter with GMA v2…",
        "nl_active_default": "NL filter active",
        "nl_json_expander": "Structured filter (JSON)",
        "mga_model_label": "Model (GMA v2)",
        "mga_test_button": "Test connection",
        "mga_test_spinner": "Testing connection to {model}…",
        "mga_test_success": "Connected to **{model}** ({dauer}s) · Response: “{antwort}”",
        "mga_test_error": "Connection to {model} failed: {fehler}",
        "indikation_label": "Indication",
        "header_1": "Patients and eyes in therapy",
        "metric_eyes_therapy": "Eyes in therapy",
        "metric_patients_therapy": "Patients in therapy",
        "metric_eyes_total": "Total eyes (filtered)",
        "metric_stichtag": "Reference date",
        "chart_indikation_x": "Indication",
        "chart_indikation_y": "Eyes in therapy",
        "header_2": "Medications and medication mix over time",
        "info_no_injections_filter": "No injections in the current filter.",
        "checkbox_normalize": "Normalize shares (100%)",
        "chart_mix_x": "Month",
        "chart_mix_y": "Injections",
        "chart_mix_color": "Medication",
        "header_3": "Interval lengths by patient, eye and medication",
        "sub_dist_by_med": "Distribution by medication",
        "info_no_intervals": "No intervals in the current filter.",
        "box_x": "Medication",
        "box_y": "Interval (days)",
        "sub_extension_after_switch": "Interval extension after medication switch",
        "info_no_switches": "No switches in the current filter.",
        "caption_example_switch": "Example: Eylea 2mg → Eylea HD (8mg) shows the mean interval change in days.",
        "expander_all_intervals": "All intervals as table",
        "header_4": "Therapy courses",
        "info_no_patients": "No patients in the current filter.",
        "select_patient_label": "Select patient",
        "info_no_injections_patient": "No injections for this patient in the current filter.",
        "caption_patient_info": "**{patient}** · Eye(s): {augen} · Indication: {indikation}",
        "timeline_x": "Date",
        "timeline_y": "Eye",
        "timeline_color": "Medication",
        "timeline_shape": "Phase",
        "visus_y": "Visual acuity (ETDRS)",
        "visus_color": "Eye",
        "label_switches_bold": "**Medication switches:**",
        "expander_all_injections": "All injections for this patient",
        "header_5": "Reconciliation of orders vs. injections",
        "metric_discrepancies": "Total discrepancies",
        "metric_records_checked": "Records checked",
        "checkbox_only_discrepancies": "Show only discrepancies",
        "sub_therapy_year": "Injections per therapy year (by indication)",
        "info_no_year_data": "No data for the therapy-year analysis in the current filter.",
        "chart_year_x": "Therapy year",
        "chart_year_y": "Injections per eye (mean)",
        "caption_year_note": (
            "As expected, higher injection load in year 1 (loading phase), decreasing afterwards. "
            "Later years are based on fewer eyes (shorter follow-up) — interpret with caution."
        ),
        "sub_all_patients_overview": "Overview of all patients in the current filter ({count})",
        "caption_grid_note_truncated": (
            "Showing {shown} of {total} patients. "
            "Color change within a tile = medication switch. Select individually below for details."
        ),
        "caption_grid_note": "Color change within a tile = medication switch. Select individually below for details.",
        "label_interval_by_eye": "**Interval trend by eye:**",
        "radio_all_eyes": "All eyes",
        "info_no_intervals_patient": "No intervals yet (at least 2 injections per eye required).",
        "chat_header": "Data analysis chat",
        "chat_caption": (
            "Ask questions in natural language about the entire dataset (independent of the filters above). "
            "GMA v2 retrieves real computations before answering."
        ),
        "chat_placeholder": "e.g. How many injections do DMOe patients need in year 1 vs. year 3 on average?",
        "chat_clear_button": "Reset chat",
        "chat_thinking": "Analyzing data…",
        "chat_tool_calls_expander": "Computations called ({count})",
        "chat_error": "Error during analysis: {fehler}",
    },
}

COLUMN_LABELS: dict[str, dict[str, str]] = {
    "patient_id": {"de": "Patient-ID", "en": "Patient ID"},
    "eye_id": {"de": "Auge-ID", "en": "Eye ID"},
    "seite": {"de": "Auge", "en": "Eye"},
    "indikation": {"de": "Indikation", "en": "Indication"},
    "praeparat": {"de": "Praeparat", "en": "Medication"},
    "datum": {"de": "Datum", "en": "Date"},
    "intervall_tage": {"de": "Intervall (Tage)", "en": "Interval (days)"},
    "praeparat_gewechselt": {"de": "Praeparat gewechselt", "en": "Medication changed"},
    "von_praeparat": {"de": "Von Praeparat", "en": "From medication"},
    "zu_praeparat": {"de": "Zu Praeparat", "en": "To medication"},
    "faelle": {"de": "Faelle", "en": "Cases"},
    "mittlere_veraenderung_tage": {"de": "Mittlere Veraenderung (Tage)", "en": "Mean change (days)"},
    "phase": {"de": "Phase", "en": "Phase"},
    "visus": {"de": "Visus", "en": "Visual acuity"},
    "monat": {"de": "Monat", "en": "Month"},
    "injektionen": {"de": "Injektionen", "en": "Injections"},
    "bestellt": {"de": "Bestellt", "en": "Ordered"},
    "differenz": {"de": "Differenz", "en": "Difference"},
    "unstimmigkeit": {"de": "Unstimmigkeit", "en": "Discrepancy"},
    "status": {"de": "Status", "en": "Status"},
}

PHASE_LABELS: dict[str, dict[str, str]] = {
    "Loading-Phase": {"de": "Loading-Phase", "en": "Loading phase"},
    "Erhaltung (Treat-and-Extend)": {"de": "Erhaltung (Treat-and-Extend)", "en": "Maintenance (treat-and-extend)"},
}

STATUS_LABELS: dict[str, dict[str, str]] = {
    "Bestellung ohne Injektion": {"de": "Bestellung ohne Injektion", "en": "Order without injection"},
    "Injektion ohne Bestellung": {"de": "Injektion ohne Bestellung", "en": "Injection without order"},
    "OK": {"de": "OK", "en": "OK"},
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: str) -> str:
    text = STRINGS.get(lang, STRINGS[DEFAULT_LANG]).get(key, key)
    return text.format(**kwargs) if kwargs else text


def rename_columns(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    mapping = {col: labels[lang] for col, labels in COLUMN_LABELS.items() if col in df.columns}
    return df.rename(columns=mapping)


def translate_values(series: pd.Series, labels: dict[str, dict[str, str]], lang: str) -> pd.Series:
    return series.map(lambda v: labels.get(v, {}).get(lang, v))
