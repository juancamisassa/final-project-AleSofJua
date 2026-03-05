# Colombia: Conflict & Mines

Interactive dashboard and academic report on armed conflict and antipersonnel mines in Colombia (1994–2024).

## Data sources and large files

The file **GEDEvent_v25_1.xlsx** (UCDP Georeferenced Event Dataset, global version 25.1) exceeds GitHub's 100 MB limit and is not included in the repo.

**To download:** Go to [UCDP Dataset Download Center](https://ucdp.uu.se/downloads/), open **Disaggregated Event Datasets** → **UCDP Georeferenced Event Dataset (GED) Global version 25.1**, and download the **Excel** version.

**Where to save:** Place the file as `data/raw-data/GEDEvent_v25_1.xlsx` (create the folder if needed). Do not rename the file.

This file is required for the presentation graph (top 10 countries by conflict events). The rest of the analysis uses `GEDEvent_Colombia.csv`, which is included in the repo.

## Project structure

| File | Description |
|------|-------------|
| `streamlit-app/app.py` | Streamlit dashboard (3 pages) |
| `final_project.qmd` | Quarto academic report with static visualizations |
| `preprocessing.py` | Central data processing module (single source of truth). Run directly to generate derived data for the dashboard |

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
python preprocessing.py
```

This generates `data/derived-data/` with geojson.json, country_outline.json and app_data.json. **Commit these files** before deploying the app.

## Run the app locally

```bash
streamlit run streamlit-app/app.py
```

## Render the final report in Quarto

The final report uses Altair for visualizations. It also uses Matplotlib for the maps. Additional requirements:

```bash
pip install altair vl-convert-python
quarto render final_project.qmd
```

## Deploy on Streamlit Community Cloud

1. Run `python preprocessing.py`
2. Commit the `data/derived-data/*.json`
3. Connect the repo to [share.streamlit.io](https://share.streamlit.io)
4. App path: `streamlit-app/app.py`
