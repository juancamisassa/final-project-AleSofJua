"""
Data wrangling for Colombia conflict and mines analysis.
All processing logic lives here. The .qmd imports this module; run directly to
generate derived data for the Streamlit app:  python code/preprocessing.py
"""
from pathlib import Path
import json
import unicodedata
import re

import pandas as pd
import geopandas as gpd

# Paths relative to code/ directory
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
OUT_DIR = DATA_DIR / "derived-data"

MANUAL_MAP = {
    ("bogota", "bogota"): "bogotadc",
    ("bogotadc", "bogota"): "bogotadc",
    ("bolivar", "cartagena"): "cartagenadeindias",
    ("nortedesantander", "cucuta"): "sanjosedecucuta",
    ("valledelcauca", "cali"): "santiagodecali",
    ("antioquia", "elsantuario"): "santuario",
    ("antioquia", "carmendeviboral"): "elcarmendeviboral",
    ("caqueta", "cartagenadelchaira"): "cartagenadelchaira",
    ("bolivar", "elcarmendebolivar"): "elcarmendebolivar",
    ("magdalena", "santamarta"): "santamarta",
    ("meta", "uribe"): "lauribe",
    ("nortedesantander", "zulia"): "elzulia",
    ("choco", "carmendeldarien"): "elcarmendeldarien",
    ("caqueta", "montanita"): "lamontanita",
    ("narino", "sanandrésdetumaco"): "tumaco",
    ("narino", "sandresdetumaco"): "tumaco",
    ("narino", "sanandresdetumaco"): "tumaco",
    ("atlantico", "sabanalargamunicipalityatlantico"): "sabanalarga",
    ("cauca", "lopezdemicay"): "lopezdemicay",
    ("caqueta", "sanjosedefragua"): "sanjosedelfragua",
    ("sucre", "sanluisdesince"): "since",
    ("antioquia", "sabanalargamunicipalityantioquia"): "sabanalarga",
}


def _first_existing_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of these columns were found: {candidates}")


def normalize(name):
    if pd.isna(name):
        return ""
    s = str(name).lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def clean_city_name(name):
    if pd.isna(name):
        return None
    name = re.sub(
        r"\s+(municipality|district|town|city)$", "", name, flags=re.IGNORECASE
    )
    return name.strip()


def load_and_process_all(data_dir=None):
    """
    Load all data and perform all merging, reshaping, and processing.
    Returns a dict with all processed objects for the qmd and app.
    """
    data_dir = data_dir or DATA_DIR
    out_dir = data_dir / "derived-data"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. GED conflict data
    df_col = pd.read_csv(data_dir / "GEDEvent_Colombia.csv")
    df_col["ciudad"] = df_col["adm_2"].apply(clean_city_name)
    mask = df_col["ciudad"].isna()
    df_col.loc[mask, "ciudad"] = df_col.loc[mask, "where_coordinates"].apply(clean_city_name)
    mask2 = df_col["ciudad"].isna()
    df_col.loc[mask2, "ciudad"] = df_col.loc[mask2, "adm_1"].apply(clean_city_name)
    df_col["departamento"] = df_col["adm_1"].apply(
        lambda x: re.sub(r"\s+(department|district)$", "", x, flags=re.IGNORECASE).strip()
        if pd.notna(x) else None
    )

    pivot = df_col.pivot_table(
        index=["departamento", "ciudad"],
        columns="year",
        values="id",
        aggfunc="count",
        fill_value=0,
    )
    pivot.columns = [str(int(y)) for y in pivot.columns]
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("Total", ascending=False)
    crimes = pivot.reset_index()

    # 2. GADM geometries
    gdf = gpd.read_file(data_dir / "gadm41_COL_2.json")
    gdf["key"] = gdf["NAME_2"].apply(normalize)
    gdf["key_dept"] = gdf["NAME_1"].apply(normalize)
    crimes["key"] = crimes["ciudad"].apply(normalize)
    crimes["key_dept"] = crimes["departamento"].apply(normalize)

    SKIP_KEYS = set()
    for _, row in crimes.iterrows():
        k = normalize(row["ciudad"])
        if "department" in str(row["ciudad"]).lower() or k == "colombia":
            SKIP_KEYS.add((normalize(row["departamento"]), k))

    geo_lookup = {}
    for idx, row in gdf.iterrows():
        geo_lookup[(row["key_dept"], row["key"])] = idx
        geo_lookup[("", row["key"])] = idx
        if pd.notna(row.get("VARNAME_2")):
            for v in str(row["VARNAME_2"]).split("|"):
                vk = normalize(v)
                if vk:
                    geo_lookup[(row["key_dept"], vk)] = idx
                    geo_lookup[("", vk)] = idx

    # 3. Match conflict to municipalities
    crime_totals = {}
    for _, crow in crimes.iterrows():
        ck, dk, total = crow["key"], crow["key_dept"], crow["Total"]
        if (dk, ck) in SKIP_KEYS:
            continue
        if (dk, ck) in MANUAL_MAP:
            ck = MANUAL_MAP[(dk, ck)]
        geo_idx = geo_lookup.get((dk, ck)) or geo_lookup.get(("", ck))
        if geo_idx is not None:
            crime_totals[geo_idx] = crime_totals.get(geo_idx, 0) + total

    gdf["crime_count"] = 0
    for idx, total in crime_totals.items():
        gdf.at[idx, "crime_count"] = int(total)

    # 4. EVENTOS 31
    ev31_path = data_dir / "EVENTOS 31_ENE_2026.xlsx"
    if not ev31_path.exists():
        raise FileNotFoundError(f"EVENTOS 31 not found. Place EVENTOS 31_ENE_2026.xlsx in {data_dir}/")
    df_ev31 = pd.read_excel(ev31_path, sheet_name=0)
    col_year = _first_existing_col(df_ev31, ["Año", "Ao", "Year", "year"])
    col_tipo = _first_existing_col(df_ev31, ["Tipo de Evento", "Tipo de evento", "Tipo Evento", "tipo_evento"])
    col_muni = _first_existing_col(df_ev31, ["Municipio", "municipio"])
    col_dept = _first_existing_col(df_ev31, ["Departamento", "departamento"])
    df_ev31 = df_ev31.rename(columns={
        col_year: "Año", col_tipo: "Tipo_Evento",
        col_muni: "Municipio", col_dept: "Departamento",
    })
    df_ev31 = df_ev31[(df_ev31["Año"] >= 1994) & (df_ev31["Año"] <= 2024)].copy()
    df_ev31["es_desminado"] = df_ev31["Tipo_Evento"].astype(str).str.contains("DESMINADO", case=False, na=False)
    df_ev31["es_map"] = df_ev31["Tipo_Evento"].astype(str).str.contains(r"MAP|ACCIDENTE", case=False, na=False, regex=True)
    df_ev31["municipio"] = df_ev31["Municipio"].astype(str).str.strip()
    df_ev31["departamento"] = df_ev31["Departamento"].astype(str).str.strip()

    # 5. EVENTOS 31 -> municipalities
    gdf["mine_count"] = 0
    gdf["mine_incidents"] = 0
    gdf["demining_count"] = 0
    ev31_agg = df_ev31.groupby(["departamento", "municipio"]).agg(
        demining_count=("es_desminado", "sum"),
        map_count=("es_map", "sum"),
    ).reset_index()
    ev31_agg["mine_incidents"] = ev31_agg["map_count"].astype(int)
    ev31_agg["mine_count"] = ev31_agg["demining_count"].astype(int) + ev31_agg["mine_incidents"]

    for _, r in ev31_agg.iterrows():
        dept_k = normalize(r["departamento"])
        muni_k = normalize(r["municipio"])
        if (dept_k, muni_k) in MANUAL_MAP:
            muni_k = MANUAL_MAP[(dept_k, muni_k)]
        geo_idx = geo_lookup.get((dept_k, muni_k)) or geo_lookup.get(("", muni_k))
        if geo_idx is not None:
            gdf.at[geo_idx, "mine_count"] += int(r["mine_count"])
            gdf.at[geo_idx, "mine_incidents"] += int(r["mine_incidents"])
            gdf.at[geo_idx, "demining_count"] += int(r["demining_count"])

    years = list(range(1994, 2025))
    desminado_anual = df_ev31.loc[df_ev31["es_desminado"]].groupby("Año").size().reindex(years, fill_value=0)
    accidentes_map_anual = df_ev31.loc[df_ev31["es_map"]].groupby("Año").size().reindex(years, fill_value=0)
    incidentes_anual = accidentes_map_anual

    desminado_por_depto = (
        df_ev31.loc[df_ev31["es_desminado"]]
        .groupby(["departamento", "Año"]).size()
        .unstack(fill_value=0)
        .reindex(columns=years, fill_value=0)
    )
    accidentes_map_por_depto = (
        df_ev31.loc[df_ev31["es_map"]]
        .groupby(["departamento", "Año"]).size()
        .unstack(fill_value=0)
        .reindex(columns=years, fill_value=0)
    )

    dem_pts = pd.DataFrame(columns=["Latitud", "Longitud", "Municipio"])
    if "Latitud" in df_ev31.columns and "Longitud" in df_ev31.columns:
        df_dem = df_ev31[df_ev31["es_desminado"]].copy()
        dem_pts = df_dem[["Latitud", "Longitud", "Municipio"]].dropna(subset=["Latitud", "Longitud"]).copy()

    # 6. CasosMI victims
    df_mi = pd.read_excel(data_dir / "CasosMI_202509.xlsx", sheet_name=0)
    col_year_mi = _first_existing_col(df_mi, ["Año", "Ao"])
    col_victims = _first_existing_col(df_mi, ["Total de Víctimas del Caso", "Total de Vctimas del Caso"])
    df_mi = df_mi[(df_mi[col_year_mi] >= 1994) & (df_mi[col_year_mi] <= 2024)]
    df_mi = df_mi[df_mi["Tipo de Armas"].str.contains(r"MINAS", case=False, na=False, regex=True)].copy()
    df_mi["victimas"] = df_mi[col_victims].fillna(0).astype(int)
    df_mi["departamento"] = df_mi["Departamento"].astype(str).str.strip()
    df_mi["municipio"] = df_mi["Municipio"].astype(str).str.strip()

    victims_by_dept_muni = df_mi.groupby(["departamento", "municipio"])["victimas"].sum().reset_index()
    gdf["total_victims"] = 0
    for _, r in victims_by_dept_muni.iterrows():
        dept_k = normalize(r["departamento"])
        muni_k = normalize(r["municipio"])
        if (dept_k, muni_k) in MANUAL_MAP:
            muni_k = MANUAL_MAP[(dept_k, muni_k)]
        geo_idx = geo_lookup.get((dept_k, muni_k)) or geo_lookup.get(("", muni_k))
        if geo_idx is not None:
            gdf.at[geo_idx, "total_victims"] += int(r["victimas"])

    # 7. Priority index
    for col in ["crime_count", "mine_incidents", "demining_count"]:
        mean_val = gdf[col].mean()
        std_val = gdf[col].std()
        if std_val == 0 or pd.isna(std_val):
            gdf[f"z_{col}"] = 0
        else:
            gdf[f"z_{col}"] = (gdf[col] - mean_val) / std_val
    gdf["priority_idx"] = (
        gdf["z_crime_count"] + gdf["z_mine_incidents"] - gdf["z_demining_count"]
    ).fillna(0).astype(float)
    gdf["gap_raw"] = (gdf["mine_incidents"] - gdf["demining_count"]).clip(lower=0).astype(int)

    # 8. Bivariate: gdf_analysis for qmd
    ev31_agg_simple = df_ev31.groupby(["departamento", "municipio"]).size().reset_index(name="minas")
    gdf_analysis = gdf[["NAME_1", "NAME_2", "CC_2", "geometry", "crime_count"]].copy()
    gdf_analysis = gdf_analysis.rename(columns={"crime_count": "conflicto"})
    gdf_analysis["minas"] = 0
    for _, r in ev31_agg_simple.iterrows():
        dept_k = normalize(r["departamento"])
        muni_k = normalize(r["municipio"])
        if (dept_k, muni_k) in MANUAL_MAP:
            muni_k = MANUAL_MAP[(dept_k, muni_k)]
        geo_idx = geo_lookup.get((dept_k, muni_k)) or geo_lookup.get(("", muni_k))
        if geo_idx is not None:
            gdf_analysis.at[geo_idx, "minas"] += int(r["minas"])
    varname_lookup = {}
    for idx_g, row_g in gdf.iterrows():
        if pd.notna(row_g.get("VARNAME_2")):
            for v in str(row_g["VARNAME_2"]).split("|"):
                varname_lookup[normalize(v)] = idx_g
    for _, row_mi in ev31_agg_simple.iterrows():
        mk = normalize(row_mi["municipio"])
        if mk in varname_lookup:
            g_idx = varname_lookup[mk]
            if gdf_analysis.at[g_idx, "minas"] == 0:
                gdf_analysis.at[g_idx, "minas"] = int(row_mi["minas"])
    gdf_analysis["key"] = gdf_analysis["NAME_2"].apply(normalize)
    gdf_analysis["key_dept"] = gdf_analysis["NAME_1"].apply(normalize)

    return {
        "df_col": df_col,
        "df_ev31": df_ev31,
        "df_mi": df_mi,
        "gdf": gdf,
        "gdf_analysis": gdf_analysis,
        "pivot": pivot,
        "geo_lookup": geo_lookup,
        "desminado_anual": desminado_anual,
        "accidentes_map_anual": accidentes_map_anual,
        "incidentes_anual": incidentes_anual,
        "desminado_por_depto": desminado_por_depto,
        "accidentes_map_por_depto": accidentes_map_por_depto,
        "dem_pts": dem_pts,
        "years": years,
        "ev31_agg_simple": ev31_agg_simple,
        "data_dir": data_dir,
        "out_dir": out_dir,
    }


def write_derived_data(data=None, data_dir=None):
    """
    Write derived-data files for the Streamlit app.
    Call after load_and_process_all(); pass the returned dict or load again.
    """
    if data is None:
        data = load_and_process_all(data_dir)
    gdf = data["gdf"]
    out_dir = data["out_dir"]
    desminado_anual = data["desminado_anual"]
    accidentes_map_anual = data["accidentes_map_anual"]
    incidentes_anual = data["incidentes_anual"]
    dem_pts = data["dem_pts"]
    desminado_por_depto = data.get("desminado_por_depto", pd.DataFrame())
    accidentes_map_por_depto = data.get("accidentes_map_por_depto", pd.DataFrame())

    gdf_simplified = gdf.copy()
    gdf_simplified["geometry"] = gdf_simplified.geometry.simplify(tolerance=0.005)
    cols_out = [
        "NAME_1", "NAME_2", "crime_count", "mine_count",
        "total_victims", "mine_incidents", "demining_count",
        "priority_idx", "gap_raw", "geometry",
    ]
    geojson_str = gdf_simplified[cols_out].to_json()

    country_geom = gdf_simplified.geometry.union_all()
    country_gdf = gpd.GeoDataFrame(geometry=[country_geom], crs=gdf_simplified.crs)
    country_outline_str = country_gdf.to_json()

    top_candidates = gdf.nlargest(20, "priority_idx")[
        ["NAME_2", "NAME_1", "priority_idx", "crime_count", "mine_incidents", "demining_count"]
    ].copy()
    top_candidates = top_candidates.drop_duplicates(subset="NAME_2", keep="first")
    top10 = top_candidates.head(20).sort_values("priority_idx", ascending=True)

    stats = {
        "conflict_events": int(gdf["crime_count"].sum()),
        "mine_events": int(gdf["mine_count"].sum()),
        "total_victims": int(gdf["total_victims"].sum()),
        "n_muni_conflict": int((gdf["crime_count"] > 0).sum()),
        "n_muni_mines": int((gdf["mine_count"] > 0).sum()),
        "n_total_muni": len(gdf),
        "demining_ops": int(gdf["demining_count"].sum()),
    }

    (out_dir / "geojson.json").write_text(geojson_str, encoding="utf-8")
    (out_dir / "country_outline.json").write_text(country_outline_str, encoding="utf-8")
    payload = {
        "desminado_anual": {int(k): int(v) for k, v in desminado_anual.to_dict().items()},
        "accidentes_map_anual": {int(k): int(v) for k, v in accidentes_map_anual.to_dict().items()},
        "incidentes_anual": {int(k): int(v) for k, v in incidentes_anual.to_dict().items()},
        "desminado_por_depto": {
            dept: {int(yr): int(v) for yr, v in row.items()}
            for dept, row in desminado_por_depto.iterrows()
        },
        "accidentes_map_por_depto": {
            dept: {int(yr): int(v) for yr, v in row.items()}
            for dept, row in accidentes_map_por_depto.iterrows()
        },
        "top10_gap": top10.to_dict(orient="records"),
        "demining_pts": dem_pts.to_dict(orient="records"),
        "stats": stats,
    }
    (out_dir / "app_data.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    print("Loading and processing all data…")
    data = load_and_process_all()
    print("Writing derived data for Streamlit app…")
    write_derived_data(data)
    print(f"Done. Output in {data['out_dir']}")
    print("  - geojson.json")
    print("  - country_outline.json")
    print("  - app_data.json")
