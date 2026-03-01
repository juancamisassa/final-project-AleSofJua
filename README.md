# Colombia: Conflict & Mines

Dashboard de conflicto armado y minas antipersonal en Colombia (1994–2024).

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

## Desplegar en Streamlit Community Cloud

1. Ejecutar `python code/preprocess_for_streamlit.py`
2. Hacer commit de `data/derived-data/*.json`
3. Conectar el repo a [share.streamlit.io](https://share.streamlit.io)
4. App path: `code/app.py`
