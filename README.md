# Colombia: Conflict & Mines

Interactive dashboard and academic report on armed conflict and antipersonnel mines in Colombia (1994–2024).

**Dashboard:** [https://final-project-alesofjua-navguezjh2t5szddznayws.streamlit.app/](https://final-project-alesofjua-navguezjh2t5szddznayws.streamlit.app/)

> **Note:** Streamlit Community Cloud apps may need to be "woken up" if they have not been run in the last 24 hours. This is normal behavior—the app will load after a short delay.

## Data sources

| Dataset | Source | Use |
|---------|--------|-----|
| **UCDP GED** (GEDEvent_v25_1.xlsx) | [UCDP Dataset Download Center](https://ucdp.uu.se/downloads/) → Disaggregated Event Datasets → UCDP Georeferenced Event Dataset (GED) Global version 25.1 | Presentation graph (top 10 countries by conflict events). *Not in repo—see below.* |
| **UCDP GED Colombia** (GEDEvent_Colombia.csv) | Subset of UCDP GED for Colombia | Conflict events by municipality |
| **AICMA** (EVENTOS 31_ENE_2026.xlsx) | Descontamina Colombia / AICMA Open Database | Demining operations and mine incidents (MAP) |
| **CasosMI** (CasosMI_202509.xlsx) | National Center for Historical Memory (CNMH for its initials in Spanish): Public database of landmine and explosive device victims from 1953 onward | Mine victims by municipality |
| **GADM** (gadm41_COL_2.json) | GADM v4.1 | Colombian municipality boundaries |

**Processing:** All wrangling is done in `preprocessing.py` (reads from `data/raw-data/`, writes to `data/derived-data/`). The `.qmd` contains this logic; run `preprocessing.py` to generate derived data for the Streamlit app.

## Large file: GEDEvent_v25_1.xlsx

The file **GEDEvent_v25_1.xlsx** (UCDP GED Global v25.1) exceeds GitHub's 100 MB limit and is not in the repo. **You must download and place this file before running `quarto render final_project.qmd`—otherwise the render will fail.**

**To download:** [Dropbox link](https://www.dropbox.com/scl/fi/1ezpmi56yz33iq1s7vdrg/GEDEvent_v25_1.xlsx?rlkey=qiitf5hvqqq7bu2yh526en4oh&st=yhm5cwq2&dl=1) (alternatively: [UCDP Dataset Download Center](https://ucdp.uu.se/downloads/) → Disaggregated Event Datasets → UCDP Georeferenced Event Dataset (GED) Global version 25.1 → Excel).

**Where to save:** `data/raw-data/GEDEvent_v25_1.xlsx` (create the folder if needed). Do not rename the file.

This file is required for the presentation graph in the writeup. The rest of the analysis uses `GEDEvent_Colombia.csv`, which is included in the repo. The file is listed in `.gitignore`.

## Reproducibility

A TA or AI agent should be able to knit the `.qmd` and regenerate the writeup (HTML or PDF).

1. **Download GED (required):** Download `GEDEvent_v25_1.xlsx` from the [Dropbox link](https://www.dropbox.com/scl/fi/1ezpmi56yz33iq1s7vdrg/GEDEvent_v25_1.xlsx?rlkey=qiitf5hvqqq7bu2yh526en4oh&st=yhm5cwq2&dl=1) (or UCDP) and place it in `data/raw-data/GEDEvent_v25_1.xlsx`. Without this step, `quarto render` will fail.
2. **Install dependencies:** `conda env create -f environment.yml`, `conda activate fire_analysis`, `pip install -r requirements.txt`, `pip install altair vl-convert-python`
3. **Render:** `quarto render final_project.qmd` (HTML and PDF) or `quarto render final_project.qmd --to pdf` for PDF only.

No file renaming is required. The `.gitignore` already excludes the large GED file.

## Project structure

| File | Description |
|------|-------------|
| `streamlit-app/app.py` | Streamlit dashboard (3 pages) |
| `final_project.qmd` | Quarto academic report with static visualizations |
| `preprocessing.py` | Central data processing. Run to generate derived data for the dashboard |

## Dashboard features

- **Page 1 — Conflict & Mine Maps**: side-by-side choropleth maps (conflict events, mine incidents, mine victims)
- **Page 2 — Demining Timeline**: line charts and proportions with interactive filters
- **Page 3 — Priority Analysis**: priority index map and top municipalities bar chart

## Setup local (development)

```bash
conda env create -f environment.yml
conda activate fire_analysis
pip install -r requirements.txt
```

## Preprocessing (required before deploying the app)

```bash
python preprocessing.py
```

This generates `data/derived-data/` (geojson.json, country_outline.json, app_data.json). **Commit these files** before deploying the app.

## Run the app locally

```bash
streamlit run streamlit-app/app.py
```

## Render the final report

```bash
pip install altair vl-convert-python
quarto render final_project.qmd
```

## Deploy on Streamlit Community Cloud

1. Run `python preprocessing.py`
2. Commit the `data/derived-data/*.json` files
3. Connect the repo to [share.streamlit.io](https://share.streamlit.io)
4. App path: `streamlit-app/app.py`
