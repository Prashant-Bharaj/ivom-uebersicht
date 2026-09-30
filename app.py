"""IVOM-Uebersicht: Streamlit-Prototyp mit erfundenen Testdaten.

Deckt die 'Ziel: Uebersicht'-Punkte aus der Projektskizze ab:
Patienten/Augen nach Indikation, Praeparatemix im Zeitverlauf, Intervalllaengen,
Therapieverlaeufe inkl. Umstellungen, Abgleich Bestellungen <-> Injektionen.

Natural-Language-Filter laufen ueber myGenAssist API v2 (/chat/completions).
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from lib import analysis_tools as at
from lib import data as ld
from lib import i18n
from lib import metrics as lm
from lib import mga
from lib import nl_filters as nl

load_dotenv(Path(__file__).resolve().parent / ".env")

st.set_page_config(page_title="IVOM-Uebersicht", layout="wide")

lang = st.sidebar.selectbox(
    i18n.t("language_label", st.session_state.get("lang", i18n.DEFAULT_LANG)),
    options=list(i18n.LANGUAGES.keys()),
    format_func=lambda code: i18n.LANGUAGES[code],
    index=list(i18n.LANGUAGES.keys()).index(st.session_state.get("lang", i18n.DEFAULT_LANG)),
    key="lang",
)


def t(key: str, **kwargs: str) -> str:
    return i18n.t(key, lang, **kwargs)


st.title(t("app_title"))
st.caption(t("app_caption"))


@st.cache_data
def load_data():
    return ld.load_all()


raw = load_data()
patients, eyes, injections, switches, orders = (
    raw["patients"],
    raw["eyes"],
    raw["injections"],
    raw["switches"],
    raw["orders"],
)

catalog = nl.catalog_from_data(eyes, injections, switches)

# --- Sidebar-Filter -----------------------------------------------------
st.sidebar.header(t("sidebar_filter_header"))

st.sidebar.subheader(t("nl_subheader"))
st.sidebar.caption(t("nl_caption"))

model_ids = [m[0] for m in mga.AVAILABLE_MODELS]
model_labels = {m[0]: m[1] for m in mga.AVAILABLE_MODELS}
default_model = mga.mga_config()["model"]
if default_model not in model_ids:
    model_ids = [default_model] + model_ids
    model_labels[default_model] = default_model
gewaehltes_modell = st.sidebar.selectbox(
    t("mga_model_label"),
    model_ids,
    index=model_ids.index(st.session_state.get("mga_model", default_model))
    if st.session_state.get("mga_model", default_model) in model_ids
    else 0,
    format_func=lambda mid: model_labels.get(mid, mid),
    key="mga_model",
)

if st.sidebar.button(t("mga_test_button")):
    with st.spinner(t("mga_test_spinner", model=gewaehltes_modell)):
        ergebnis = mga.test_connection(gewaehltes_modell)
    if ergebnis["ok"]:
        st.sidebar.success(
            t(
                "mga_test_success",
                model=gewaehltes_modell,
                dauer=str(ergebnis["dauer_s"]),
                antwort=ergebnis["antwort"],
            )
        )
    else:
        st.sidebar.error(
            t("mga_test_error", model=gewaehltes_modell, fehler=ergebnis["fehler"])
        )

nl_query = st.sidebar.text_area(
    "Filter beschreiben",
    value=st.session_state.get("nl_query_text", ""),
    height=90,
    placeholder=t("nl_placeholder"),
    label_visibility="collapsed",
)
col_nl1, col_nl2 = st.sidebar.columns(2)
apply_nl = col_nl1.button(t("btn_apply"), use_container_width=True, type="primary")
clear_nl = col_nl2.button(t("btn_reset"), use_container_width=True)

if clear_nl:
    st.session_state.pop("nl_filters", None)
    st.session_state.pop("nl_query_text", None)
    st.session_state.pop("nl_error", None)
    st.rerun()

if apply_nl:
    st.session_state["nl_query_text"] = nl_query
    st.session_state.pop("nl_error", None)
    if not nl_query.strip():
        st.session_state["nl_error"] = t("err_empty_query")
    else:
        try:
            with st.spinner(t("nl_spinner")):
                st.session_state["nl_filters"] = nl.parse_nl_query(
                    nl_query, catalog, model=gewaehltes_modell
                )
        except Exception as exc:  # noqa: BLE001 — show upstream/API errors in UI
            st.session_state["nl_error"] = str(exc)
            st.session_state.pop("nl_filters", None)

if st.session_state.get("nl_error"):
    st.sidebar.error(st.session_state["nl_error"])

nl_active = st.session_state.get("nl_filters")
if nl.filters_active(nl_active):
    st.sidebar.success(nl_active.get("erklaerung") or t("nl_active_default"))
    with st.sidebar.expander(t("nl_json_expander"), expanded=False):
        st.json({k: v for k, v in nl_active.items() if k != "erklaerung"})

indikationen = catalog["indikationen"]
default_ind = (
    nl_active["indikationen"]
    if nl.filters_active(nl_active) and nl_active.get("indikationen")
    else indikationen
)
gewaehlte_indikationen = st.sidebar.multiselect(
    t("indikation_label"),
    indikationen,
    default=[i for i in default_ind if i in indikationen] or indikationen,
)

# Basis: Multiselect; bei aktivem NL-Filter zusaetzliche Dimensionen aus GMA
eyes_f = eyes[eyes["indikation"].isin(gewaehlte_indikationen)]
injections_f = injections[injections["eye_id"].isin(eyes_f["eye_id"])]
orders_f = orders[orders["patient_id"].isin(eyes_f["patient_id"].unique())]
switches_f = switches[switches["eye_id"].isin(eyes_f["eye_id"])]

if nl.filters_active(nl_active):
    # Indikation bereits per Multiselect — im NL-Payload nur die restlichen Felder
    overlay = dict(nl_active)
    overlay["indikationen"] = None
    filtered = nl.apply_filters(
        overlay,
        eyes=eyes_f,
        injections=injections_f,
        orders=orders_f,
        switches=switches_f,
    )
    eyes_f = filtered["eyes"]
    injections_f = filtered["injections"]
    orders_f = filtered["orders"]
    switches_f = filtered["switches"]

stichtag = pd.Timestamp(injections["datum"].max())

# --- 1. KPI-Kopfzeile -----------------------------------------------------
st.header(t("header_1"))

status = ld.eyes_in_therapie(eyes_f, injections_f, stichtag)
aktive_augen = status[status["in_therapie"]]

col1, col2, col3, col4 = st.columns(4)
col1.metric(t("metric_eyes_therapy"), int(aktive_augen.shape[0]))
col2.metric(t("metric_patients_therapy"), aktive_augen["patient_id"].nunique())
col3.metric(t("metric_eyes_total"), int(eyes_f.shape[0]))
col4.metric(t("metric_stichtag"), stichtag.date().isoformat())

nach_indikation = (
    aktive_augen.groupby("indikation").size().reindex(indikationen, fill_value=0).reset_index(name="augen_in_therapie")
)
chart_indikation = (
    alt.Chart(nach_indikation)
    .mark_bar()
    .encode(
        x=alt.X("indikation:N", title=t("chart_indikation_x")),
        y=alt.Y("augen_in_therapie:Q", title=t("chart_indikation_y")),
        tooltip=["indikation", "augen_in_therapie"],
    )
    .properties(height=250)
)
st.altair_chart(chart_indikation, use_container_width=True)

# --- Datenanalyse-Chat (arbeitet auf dem gesamten Datensatz, unabhaengig von Filtern) ---
st.header(t("chat_header"))
st.caption(t("chat_caption"))

if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []

for eintrag in st.session_state["chat_messages"]:
    with st.chat_message(eintrag["role"]):
        st.markdown(eintrag["content"])
        if eintrag.get("tool_calls"):
            with st.expander(t("chat_tool_calls_expander", count=str(len(eintrag["tool_calls"])))):
                for tc in eintrag["tool_calls"]:
                    st.code(f"{tc['name']}({tc['arguments']})", language="python")

chat_frage = st.chat_input(t("chat_placeholder"))

if st.session_state["chat_messages"] and st.button(t("chat_clear_button")):
    st.session_state["chat_messages"] = []
    st.rerun()

if chat_frage:
    st.session_state["chat_messages"].append({"role": "user", "content": chat_frage})
    with st.chat_message("user"):
        st.markdown(chat_frage)

    verlauf_fuer_gma = [
        {"role": "system", "content": (
            "Du bist ein Datenanalyse-Assistent fuer eine Augenarztpraxis (IVOM-Therapie). "
            "Nutze IMMER die bereitgestellten Tools um Fragen mit echten Zahlen aus den Praxisdaten "
            "zu beantworten — erfinde keine Zahlen. Antworte praezise, mit konkreten Werten, in der "
            "Sprache der Frage."
        )}
    ] + [{"role": m["role"], "content": m["content"]} for m in st.session_state["chat_messages"]]

    aufgerufene_tools: list[dict] = []

    def _execute_tool(name: str, arguments: dict) -> dict:
        aufgerufene_tools.append({"name": name, "arguments": arguments})
        return at.execute_tool(name, arguments, raw)

    with st.chat_message("assistant"):
        with st.spinner(t("chat_thinking")):
            try:
                antwort, _ = mga.chat_with_tools(
                    verlauf_fuer_gma,
                    at.TOOL_SPECS,
                    _execute_tool,
                    model=gewaehltes_modell,
                    max_tokens=1024,
                )
            except Exception as exc:  # noqa: BLE001 — Fehler im Chat anzeigen statt Crash
                antwort = t("chat_error", fehler=str(exc))

        st.markdown(antwort)
        if aufgerufene_tools:
            with st.expander(t("chat_tool_calls_expander", count=str(len(aufgerufene_tools)))):
                for tc in aufgerufene_tools:
                    st.code(f"{tc['name']}({tc['arguments']})", language="python")

    st.session_state["chat_messages"].append(
        {"role": "assistant", "content": antwort, "tool_calls": aufgerufene_tools}
    )

# --- 2. Praeparate im Zeitverlauf -----------------------------------------
st.header(t("header_2"))

mix = lm.medikamenten_mix_monatlich(injections_f)
if mix.empty:
    st.info(t("info_no_injections_filter"))
else:
    chart_mix = (
        alt.Chart(mix)
        .mark_area()
        .encode(
            x=alt.X("monat:T", title=t("chart_mix_x")),
            y=alt.Y(
                "anzahl:Q",
                title=t("chart_mix_y"),
                stack="normalize" if st.checkbox(t("checkbox_normalize"), value=False) else "zero",
            ),
            color=alt.Color("praeparat:N", title=t("chart_mix_color")),
            tooltip=["monat", "praeparat", "anzahl"],
        )
        .properties(height=350)
    )
    st.altair_chart(chart_mix, use_container_width=True)

# --- 3. Intervalllaengen ----------------------------------------------------
st.header(t("header_3"))

intervals = lm.compute_intervals(injections_f)
intervall_tab = lm.intervall_uebersicht(intervals, eyes_f)

col_a, col_b = st.columns([1, 2])
with col_a:
    st.subheader(t("sub_dist_by_med"))
    if intervall_tab.empty:
        st.info(t("info_no_intervals"))
    else:
        box = (
            alt.Chart(intervall_tab)
            .mark_boxplot()
            .encode(x=alt.X("praeparat:N", title=t("box_x")), y=alt.Y("intervall_tage:Q", title=t("box_y")))
            .properties(height=350)
        )
        st.altair_chart(box, use_container_width=True)

with col_b:
    st.subheader(t("sub_extension_after_switch"))
    verlaengerung = lm.intervall_verlaengerung_nach_umstellung(intervals, switches_f)
    if verlaengerung.empty:
        st.info(t("info_no_switches"))
    else:
        zusammenfassung = (
            verlaengerung.groupby(["von_praeparat", "zu_praeparat"])
            .agg(faelle=("eye_id", "count"), mittlere_veraenderung_tage=("veraenderung_tage", "mean"))
            .reset_index()
            .round(1)
        )
        st.dataframe(i18n.rename_columns(zusammenfassung, lang), use_container_width=True, hide_index=True)
        st.caption(t("caption_example_switch"))

with st.expander(t("expander_all_intervals")):
    st.dataframe(
        i18n.rename_columns(intervall_tab.sort_values("datum", ascending=False), lang),
        use_container_width=True,
        hide_index=True,
    )

st.subheader(t("sub_therapy_year"))
inj_mit_jahr = lm.add_relative_time(injections_f, eyes_f)
jahres_uebersicht = lm.injektionen_pro_therapiejahr(inj_mit_jahr)
if jahres_uebersicht.empty:
    st.info(t("info_no_year_data"))
else:
    chart_jahr = (
        alt.Chart(jahres_uebersicht)
        .mark_bar()
        .encode(
            x=alt.X("therapiejahr_label:N", title=t("chart_year_x"), sort=None),
            y=alt.Y("mittlere_injektionen:Q", title=t("chart_year_y")),
            color=alt.Color("indikation:N", title=t("indikation_label")),
            column=alt.Column("indikation:N", title=None),
            tooltip=["indikation", "therapiejahr_label", "mittlere_injektionen", "anzahl_augen"],
        )
        .properties(height=280, width=150)
    )
    st.altair_chart(chart_jahr, use_container_width=False)
    st.caption(t("caption_year_note"))

# --- 4. Therapieverlaeufe (Patient Journey) --------------------------------
st.header(t("header_4"))

patienten_liste = sorted(eyes_f["patient_id"].unique())
if not patienten_liste:
    st.info(t("info_no_patients"))
else:
    st.subheader(t("sub_all_patients_overview", count=str(len(patienten_liste))))
    max_kacheln = 30
    patienten_fuer_grid = patienten_liste[:max_kacheln]
    grid_daten = injections_f[injections_f["patient_id"].isin(patienten_fuer_grid)].merge(
        eyes_f[["eye_id", "seite"]], on="eye_id", how="left"
    )
    grid_chart = (
        alt.Chart(grid_daten)
        .mark_point(size=25, filled=True)
        .encode(
            x=alt.X("datum:T", axis=alt.Axis(labels=False, ticks=False), title=None),
            y=alt.Y("seite:N", axis=alt.Axis(labels=False, ticks=False), title=None),
            color=alt.Color("praeparat:N", title=t("chart_mix_color")),
            tooltip=["patient_id", "datum", "seite", "praeparat"],
        )
        .properties(width=130, height=50)
        .facet(facet=alt.Facet("patient_id:N", title=None), columns=6)
        .resolve_scale(x="independent")
    )
    st.altair_chart(grid_chart, use_container_width=False)
    if len(patienten_liste) > max_kacheln:
        st.caption(
            t(
                "caption_grid_note_truncated",
                shown=str(max_kacheln),
                total=str(len(patienten_liste)),
            )
        )
    else:
        st.caption(t("caption_grid_note"))

    gewaehlter_patient = st.selectbox(t("select_patient_label"), patienten_liste)

    patient_eyes = eyes_f[eyes_f["patient_id"] == gewaehlter_patient]
    patient_inj = injections_f[injections_f["patient_id"] == gewaehlter_patient].merge(
        eyes_f[["eye_id", "seite", "indikation"]], on="eye_id", how="left"
    )
    patient_switches = switches_f[switches_f["eye_id"].isin(patient_eyes["eye_id"])].merge(
        eyes_f[["eye_id", "seite"]], on="eye_id", how="left"
    )

    if patient_inj.empty:
        st.info(t("info_no_injections_patient"))
    else:
        patient_inj = lm.mark_phase(patient_inj)

        seiten_vorhanden = sorted(patient_inj["seite"].unique())
        auge_label = ", ".join(seiten_vorhanden)
        indikation_label = ", ".join(sorted(patient_inj["indikation"].dropna().unique()))
        st.caption(t("caption_patient_info", patient=gewaehlter_patient, augen=auge_label, indikation=indikation_label))

        patient_inj_anzeige = patient_inj.copy()
        patient_inj_anzeige["phase"] = i18n.translate_values(patient_inj_anzeige["phase"], i18n.PHASE_LABELS, lang)

        punkte = (
            alt.Chart(patient_inj_anzeige)
            .mark_point(size=110, filled=True)
            .encode(
                x=alt.X("datum:T", title=t("timeline_x")),
                y=alt.Y("seite:N", title=t("timeline_y")),
                color=alt.Color("praeparat:N", title=t("timeline_color")),
                shape=alt.Shape("phase:N", title=t("timeline_shape")),
                tooltip=["datum", "seite", "praeparat", "phase", "visus"],
            )
        )

        if not patient_switches.empty:
            switch_regeln = (
                alt.Chart(patient_switches)
                .mark_rule(color="firebrick", strokeDash=[4, 3], size=2)
                .encode(
                    x="datum:T",
                    tooltip=["datum", "seite", "von_praeparat", "zu_praeparat"],
                )
            )
            timeline = (punkte + switch_regeln)
        else:
            timeline = punkte

        st.altair_chart(timeline.properties(height=220), use_container_width=True)

        visus_verlauf = (
            alt.Chart(patient_inj)
            .mark_line(point=True)
            .encode(
                x=alt.X("datum:T", title=t("timeline_x")),
                y=alt.Y("visus:Q", title=t("visus_y"), scale=alt.Scale(zero=False)),
                color=alt.Color("seite:N", title=t("visus_color")),
                tooltip=["datum", "seite", "praeparat", "visus"],
            )
            .properties(height=160)
        )
        st.altair_chart(visus_verlauf, use_container_width=True)

        st.write(t("label_interval_by_eye"))
        augen_optionen = [t("radio_all_eyes")] + seiten_vorhanden
        gewaehlte_seite = st.radio("Auge fuer Intervallverlauf", augen_optionen, horizontal=True, label_visibility="collapsed")
        patient_intervalle = lm.compute_intervals(patient_inj).dropna(subset=["intervall_tage"])
        if gewaehlte_seite != t("radio_all_eyes"):
            patient_intervalle = patient_intervalle[patient_intervalle["seite"] == gewaehlte_seite]

        if patient_intervalle.empty:
            st.info(t("info_no_intervals_patient"))
        else:
            interval_verlauf = (
                alt.Chart(patient_intervalle)
                .mark_line(point=True)
                .encode(
                    x=alt.X("datum:T", title=t("timeline_x")),
                    y=alt.Y("intervall_tage:Q", title=t("box_y")),
                    color=alt.Color("seite:N", title=t("visus_color")),
                    tooltip=["datum", "seite", "praeparat", "intervall_tage"],
                )
                .properties(height=160)
            )
            st.altair_chart(interval_verlauf, use_container_width=True)

        if not patient_switches.empty:
            st.write(t("label_switches_bold"))
            st.dataframe(
                i18n.rename_columns(
                    patient_switches[["datum", "seite", "von_praeparat", "zu_praeparat"]], lang
                ),
                use_container_width=True,
                hide_index=True,
            )

        with st.expander(t("expander_all_injections")):
            patient_inj_tabelle = patient_inj[["datum", "seite", "praeparat", "phase", "visus"]].sort_values(
                "datum", ascending=False
            ).copy()
            patient_inj_tabelle["phase"] = i18n.translate_values(patient_inj_tabelle["phase"], i18n.PHASE_LABELS, lang)
            st.dataframe(
                i18n.rename_columns(patient_inj_tabelle, lang),
                use_container_width=True,
                hide_index=True,
            )

# --- 5. Abgleich Bestellungen <-> Injektionen -------------------------------
st.header(t("header_5"))

abgleich = lm.abgleich_bestellungen_injektionen(orders_f, injections_f)
unstimmig = abgleich[abgleich["unstimmigkeit"]]

col5, col6 = st.columns(2)
col5.metric(t("metric_discrepancies"), int(unstimmig.shape[0]))
col6.metric(t("metric_records_checked"), int(abgleich.shape[0]))

nur_unstimmig = st.checkbox(t("checkbox_only_discrepancies"), value=True)
anzeige = (unstimmig if nur_unstimmig else abgleich).sort_values("monat", ascending=False).copy()
anzeige["status"] = i18n.translate_values(anzeige["status"], i18n.STATUS_LABELS, lang)
st.dataframe(
    i18n.rename_columns(anzeige, lang),
    use_container_width=True,
    hide_index=True,
)
