# Colombia: Conflict & Mines

Interactive dashboard and academic report on armed conflict and antipersonnel mines in Colombia (1994–2024).

## Project structure

| File | Description |
|------|-------------|
| `code/app.py` | Streamlit dashboard (3 pages) |
| `code/Final_project.qmd` | Quarto academic report with static visualizations |
| `code/wrangling.py` | Central data processing module (single source of truth) |
| `code/preprocess_for_streamlit.py` | Generates derived JSON files for the dashboard |

## Dashboard features

- **Page 1 — Conflict & Mine Maps**: side-by-side choropleth maps (conflict events, mine accidents, mine victims)
- **Page 2 — Demining Timeline**: line charts and proportions with interactive filters (department selector, year range slider)
- **Page 3 — Priority Analysis**: priority index map and ranked bar chart with adjustable number of municipalities (5–20)

## Setup local (development)

```bash
conda env create -f environment.yml
conda activate fire_analysis
pip install -r requirements.txt
```

## Preprocessing of the Data (required before deploying the app)

The dashboard on Streamlit Cloud uses preprocesed data to avoid the use of geopandas during runtime:

```bash
python code/preprocess_for_streamlit.py
```

This generates `data/derived-data/` with geojson.json, country_outline.json and app_data.json. **Commit these files** before deploying the app.

## Run the app locally

```bash
streamlit run code/app.py
```

## Render the final report in Quarto

The final report uses Altair for visualizations. It also uses Matplotlib for the maps. Additional requirements:

```bash
pip install altair vl-convert-python
quarto render code/Final_project.qmd
```

## Deploy on Streamlit Community Cloud

1. Run `python code/preprocess_for_streamlit.py`
2. Commit the `data/derived-data/*.json`
3. Connect the repo to [share.streamlit.io](https://share.streamlit.io)
4. App path: `code/app.py`
