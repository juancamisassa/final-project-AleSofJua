"""
Preprocess data for Streamlit deployment.
Run locally (requires geopandas) to generate lightweight JSON files.
The deployed app loads these directly — no geopandas needed at runtime.
"""
from pathlib import Path
import json
import unicodedata
import re

import pandas as pd
import geopandas as gpd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
OUT_DIR = DATA_DIR / "derived-data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Eventos 31: archivo opcional para desminado + accidentes MAP (solo conteos).
# CasosMI se sigue usando para conteo de víctimas. Se buscan en este orden:
EVENTOS_31_PATHS = [
    DATA_DIR / "EVENTOS 31_ENE_2026.xlsx",
]


def _first_existing_col(df: pd.DataFrame, candidates):
    """Return the first column name from `candidates` that exists in df.columns."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of these columns were found: {candidates}")


def _clean_dane_code(x) -> str:
    """Normalize DANE municipality code as a 5‑digit string, preserving leading zeros."""
    if pd.isna(x):
        return ""
    s = str(x).strip()
    # Common Excel artifact: 52835.0
    s = re.sub(r"\.0$", "", s)
    # Keep only digits
    s = re.sub(r"\D", "", s)
    if not s:
        return ""
    if len(s) < 5:
        s = s.zfill(5)
    return s


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


def _load_eventos31():
    """
    Carga el archivo Eventos 31 si existe (Excel o CSV).
    Columnas esperadas: Año, Tipo de Evento, Municipio, Departamento,
    opcional Código DANE. Retorna DataFrame con Año, es_desminado, es_map,
    municipio, departamento; o None si no se encuentra el archivo.
    """
    path = None
    for p in EVENTOS_31_PATHS:
        if p.exists():
            path = p
            break
    if path is None:
        return None

    print(f"Cargando Eventos 31 desde {path.name}...")
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, encoding="utf-8-sig")
    else:
        df = pd.read_excel(path, sheet_name=0)

    col_year = _first_existing_col(df, ["Año", "Ao", "Year", "year"])
    col_tipo = _first_existing_col(
        df, ["Tipo de Evento", "Tipo de evento", "Tipo Evento", "tipo_evento"]
    )
    col_muni = _first_existing_col(df, ["Municipio", "municipio"])
    col_dept = _first_existing_col(df, ["Departamento", "departamento"])
    col_dane = None
    for c in ["Código DANE de Municipio", "Cdigo DANE de Municipio", "Código DANE", "DANE", "dane_muni"]:
        if c in df.columns:
            col_dane = c
            break

    df = df.rename(columns={
        col_year: "Año",
        col_tipo: "Tipo_Evento",
        col_muni: "Municipio",
        col_dept: "Departamento",
    })
    df = df[(df["Año"] >= 1994) & (df["Año"] <= 2024)].copy()
    df["es_desminado"] = df["Tipo_Evento"].astype(str).str.contains(
        "DESMINADO", case=False, na=False
    )
    df["es_map"] = df["Tipo_Evento"].astype(str).str.contains(
        r"MAP|ACCIDENTE", case=False, na=False, regex=True
    )
    if col_dane:
        df["dane_muni"] = df[col_dane].apply(_clean_dane_code)
    else:
        df["dane_muni"] = ""
    df["municipio"] = df["Municipio"].astype(str).str.strip()
    df["departamento"] = df["Departamento"].astype(str).str.strip()
    return df


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


def main():
    print("Loading GEDEvent...")
    df_col = pd.read_csv(DATA_DIR / "GEDEvent_Colombia.csv")
    df_col["ciudad"] = df_col["adm_2"].apply(clean_city_name)
    mask = df_col["ciudad"].isna()
    df_col.loc[mask, "ciudad"] = df_col.loc[mask, "where_coordinates"].apply(
        clean_city_name
    )
    mask2 = df_col["ciudad"].isna()
    df_col.loc[mask2, "ciudad"] = df_col.loc[mask2, "adm_1"].apply(
        clean_city_name
    )
    df_col["departamento"] = df_col["adm_1"].apply(
        lambda x: re.sub(
            r"\s+(department|district)$", "", x, flags=re.IGNORECASE
        ).strip()
        if pd.notna(x)
        else None
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
    crimes = pivot.reset_index()

    print("Loading GeoJSON...")
    gdf = gpd.read_file(DATA_DIR / "gadm41_COL_2.json")
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

    gdf["mine_count"] = 0
    gdf["total_victims"] = 0
    gdf["mine_incidents"] = 0
    gdf["demining_count"] = 0

    years = list(range(1994, 2025))
    df_ev31 = _load_eventos31()
    if df_ev31 is None:
        raise FileNotFoundError(
            "EVENTOS 31 no encontrado. Coloca EVENTOS 31_ENE_2026.xlsx en data/"
        )

    # EVENTOS 31: demining_count, mine_incidents (MAP), mine_count
    ev31_agg = df_ev31.groupby(["departamento", "municipio"]).agg(
        demining_count=("es_desminado", "sum"),
        map_count=("es_map", "sum"),
    ).reset_index()
    ev31_agg["mine_incidents"] = ev31_agg["map_count"].astype(int)
    ev31_agg["mine_count"] = (
        ev31_agg["demining_count"].astype(int) + ev31_agg["mine_incidents"]
    )
    match_rows = []
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
        match_rows.append({
            "departamento": r["departamento"], "municipio": r["municipio"],
            "mine_count": int(r["mine_count"]),
            "mine_incidents": int(r["mine_incidents"]),
            "demining_count": int(r["demining_count"]),
            "matched": geo_idx is not None,
        })
    report = pd.DataFrame(match_rows)
    desminado_anual = (
        df_ev31.loc[df_ev31["es_desminado"]]
        .groupby("Año").size()
        .reindex(years, fill_value=0)
    )
    accidentes_map_anual = (
        df_ev31.loc[df_ev31["es_map"]]
        .groupby("Año").size()
        .reindex(years, fill_value=0)
    )
    incidentes_anual = accidentes_map_anual
    df_demining = df_ev31[df_ev31["es_desminado"]].copy()
    if "Latitud" in df_ev31.columns and "Longitud" in df_ev31.columns:
        dem_pts = (
            df_demining[["Latitud", "Longitud", "Municipio"]]
            .dropna(subset=["Latitud", "Longitud"])
            .copy()
        )
    else:
        dem_pts = pd.DataFrame(columns=["Latitud", "Longitud", "Municipio"])
    print("Cargando CasosMI (solo víctimas)...")
    df_mi = pd.read_excel(DATA_DIR / "CasosMI_202509.xlsx", sheet_name=0)
    col_year = _first_existing_col(df_mi, ["Año", "Ao"])
    col_victims = _first_existing_col(
        df_mi, ["Total de Víctimas del Caso", "Total de Vctimas del Caso"]
    )
    df_mi = df_mi[(df_mi[col_year] >= 1994) & (df_mi[col_year] <= 2024)]
    df_mi = df_mi[
        df_mi["Tipo de Armas"].str.contains(r"MINAS", case=False, na=False, regex=True)
    ].copy()
    df_mi["victimas"] = df_mi[col_victims].fillna(0).astype(int)
    df_mi["departamento"] = df_mi["Departamento"].astype(str).str.strip()
    df_mi["municipio"] = df_mi["Municipio"].astype(str).str.strip()
    victims_by_dept_muni = (
        df_mi.groupby(["departamento", "municipio"])["victimas"].sum().reset_index()
    )
    for _, r in victims_by_dept_muni.iterrows():
        dept_k = normalize(r["departamento"])
        muni_k = normalize(r["municipio"])
        if (dept_k, muni_k) in MANUAL_MAP:
            muni_k = MANUAL_MAP[(dept_k, muni_k)]
        geo_idx = geo_lookup.get((dept_k, muni_k)) or geo_lookup.get(("", muni_k))
        if geo_idx is not None:
            gdf.at[geo_idx, "total_victims"] += int(r["victimas"])

    unmatched = report[~report["matched"]].copy()
    if "mine_count" in unmatched.columns:
        unmatched = unmatched.sort_values("mine_count", ascending=False)
    report.to_csv(OUT_DIR / "mine_matching_report.csv", index=False, encoding="utf-8-sig")
    unmatched.to_csv(OUT_DIR / "unmatched_mines.csv", index=False, encoding="utf-8-sig")
    print(
        f"Eventos 31: {len(df_ev31)} eventos; "
        f"desminado {int(desminado_anual.sum())}, MAP {int(accidentes_map_anual.sum())}; "
        f"víctimas (CasosMI): {int(gdf['total_victims'].sum())}",
    )

    gdf["gap_raw"] = (
        (gdf["mine_incidents"] - gdf["demining_count"]).clip(lower=0).astype(int)
    )

    print("Simplifying geometry...")
    gdf["geometry"] = gdf.geometry.simplify(tolerance=0.005)

    cols_out = [
        "NAME_1", "NAME_2", "crime_count", "mine_count",
        "total_victims", "mine_incidents", "demining_count",
        "gap_raw", "geometry",
    ]
    geojson_str = gdf[cols_out].to_json()

    print("Building country outline...")
    country_geom = gdf.geometry.union_all()
    country_gdf = gpd.GeoDataFrame(geometry=[country_geom], crs=gdf.crs)
    country_outline_str = country_gdf.to_json()

    gdf["incidents_minus_demining"] = (
        gdf["mine_incidents"] - gdf["demining_count"]
    )
    top_candidates = gdf.nlargest(20, "incidents_minus_demining")[
        [
            "NAME_2", "NAME_1", "incidents_minus_demining",
            "mine_incidents", "demining_count",
        ]
    ].copy()
    top_candidates = top_candidates.drop_duplicates(subset="NAME_2", keep="first")
    top10 = top_candidates.head(10).sort_values(
        "incidents_minus_demining", ascending=True
    )

    stats = {
        "conflict_events": int(gdf["crime_count"].sum()),
        "mine_events": int(gdf["mine_count"].sum()),
        "total_victims": int(gdf["total_victims"].sum()),
        "n_muni_conflict": int((gdf["crime_count"] > 0).sum()),
        "n_muni_mines": int((gdf["mine_count"] > 0).sum()),
        "n_total_muni": len(gdf),
        "demining_ops": int(gdf["demining_count"].sum()),
    }

    # Save all preprocessed data
    (OUT_DIR / "geojson.json").write_text(geojson_str, encoding="utf-8")
    (OUT_DIR / "country_outline.json").write_text(
        country_outline_str, encoding="utf-8"
    )

    payload = {
        "desminado_anual": {int(k): int(v) for k, v in desminado_anual.to_dict().items()},
        "accidentes_map_anual": {int(k): int(v) for k, v in accidentes_map_anual.to_dict().items()},
        "incidentes_anual": {int(k): int(v) for k, v in incidentes_anual.to_dict().items()},
        "top10_gap": top10.to_dict(orient="records"),
        "demining_pts": dem_pts.to_dict(orient="records"),
        "stats": stats,
    }
    (OUT_DIR / "app_data.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    print(f"Done. Output in {OUT_DIR}")
    print(f"  - geojson.json ({len(geojson_str) / 1024:.1f} KB)")
    print(f"  - country_outline.json ({len(country_outline_str) / 1024:.1f} KB)")
    print(f"  - app_data.json")


if __name__ == "__main__":
    main()
