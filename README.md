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

## Setup local (desarrollo)

```bash
conda env create -f environment.yml
conda activate fire_analysis
pip install -r requirements.txt
```

## Preprocesar datos (requerido antes de desplegar)

El dashboard en Streamlit Cloud usa datos preprocesados para evitar geopandas en runtime:

```bash
python code/preprocess_for_streamlit.py
```

Esto genera `data/derived-data/` con geojson.json, country_outline.json y app_data.json. **Commitear estos archivos** antes de desplegar.

## Ejecutar localmente

```bash
streamlit run code/app.py
```

## Renderizar el reporte Quarto

El reporte usa Altair (además de Matplotlib) para visualizaciones. Requisitos adicionales:

```bash
pip install altair vl-convert-python
quarto render code/Final_project.qmd
```

## Desplegar en Streamlit Community Cloud

1. Ejecutar `python code/preprocess_for_streamlit.py`
2. Hacer commit de `data/derived-data/*.json`
3. Conectar el repo a [share.streamlit.io](https://share.streamlit.io)
4. App path: `code/app.py`
