# IVOM-Uebersicht (Prototyp)

Prototyp fuer die Vibe-Coding-Session, DOG-Kongress 2026. Arbeitet ausschliesslich
mit erfundenen Testdaten (siehe `IVOM_Uebersicht_Projektskizze.pdf`).

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env   # MGA_API_KEY setzen (gleicher mga-... Token wie voice-desk)
python generate_data.py   # erzeugt data/*.csv mit Testdaten
streamlit run app.py
```

Die App oeffnet sich unter http://localhost:8501.

Fuer Natural-Language-Filter in der Sidebar braucht die App Zugang zu
`https://chat.int.bayer.com/api/v2/chat/completions` (Bayer-Netz) und
`MGA_API_KEY` in `.env`. Ohne Key bleiben die klassischen Multiselect-Filter nutzbar.

## Struktur

- `generate_data.py` – erzeugt synthetische Patienten, Augen, Injektionen,
  Praeparatumstellungen und Bestellungen (inkl. absichtlicher Unstimmigkeiten)
  in `data/*.csv`. Erneut ausfuehren, um den Datensatz neu zu erzeugen.
- `lib/data.py` – laedt die CSVs.
- `lib/metrics.py` – Intervallberechnung, Praeparatemix, Abgleich Bestellungen/Injektionen.
- `lib/mga.py` – myGenAssist v2 chat/completions Client.
- `lib/nl_filters.py` – NL-Anfrage → strukturierte Filter → DataFrame-Filter.
- `app.py` – Streamlit-Dashboard mit den fuenf Uebersichts-Bereichen aus der
  Projektskizze plus NL-Kohortenfilter in der Sidebar.

## Naechste Schritte (nicht Teil dieses Prototyps)

Freier Daten-Chat, Bilddaten-Analyse (OCT-Export) und Vernetzung zwischen Praxen
sind laut Projektskizze spaetere Ausbaustufen.
