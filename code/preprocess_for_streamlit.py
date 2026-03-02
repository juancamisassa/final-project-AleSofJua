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

def _first_existing_col(df: pd.DataFrame, candidates: list[str]) -> str:
    """Return the first column name that exists in df.

    This project has been edited on different machines/locales; some consoles show
    mojibake (e.g. 'A�o' instead of 'Año'). This helper keeps preprocessing robust.
    """
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of these columns were found: {candidates}")


def _clean_dane_code(x) -> str:
    """Normalize DANE municipality code as digits (keep leading zeros)."""
    if pd.isna(x):
        return ""
    s = str(x).strip()
    # Common Excel import artifact: 52835.0
    s = re.sub(r"\.0$", "", s)
    s = re.sub(r"\D", "", s)
    if not s:
        return ""
    # Municipality DANE codes are typically 5 digits (DDMMM)
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

    print("Loading CasosMI...")
    df_mi = pd.read_excel(DATA_DIR / "CasosMI_202509.xlsx", sheet_name=0)
    col_year = _first_existing_col(df_mi, ["Año", "A�o"])
    col_dane_muni = _first_existing_col(
        df_mi, ["Código DANE de Municipio", "C�digo DANE de Municipio"]
    )
    col_victims = _first_existing_col(
        df_mi, ["Total de Víctimas del Caso", "Total de V�ctimas del Caso"]
    )

    df_mi = df_mi[(df_mi[col_year] >= 1994) & (df_mi[col_year] <= 2024)]
    df_mi = df_mi[
        df_mi["Tipo de Armas"].str.contains(
            r"MINAS", case=False, na=False, regex=True
        )
    ].copy()
    df_mi["es_desminado_all"] = df_mi["Tipo de Evento"].str.contains(
        "DESMINADO", case=False, na=False
    )
    df_mi["victimas"] = (
        df_mi[col_victims].fillna(0).astype(int)
    )
    df_mi["dane_muni"] = df_mi[col_dane_muni].apply(_clean_dane_code)

    df_mi_incidents = df_mi[~df_mi["es_desminado_all"]]
    df_demining = df_mi[df_mi["es_desminado_all"]]

    gdf["mine_count"] = 0
    gdf["total_victims"] = 0
    gdf["mine_incidents"] = 0
    gdf["demining_count"] = 0

    # Aggregate mines by DANE code (prevents name-variant fragmentation)
    mines_by_dane = (
        df_mi.groupby("dane_muni")
        .agg(
            mine_count=("ID Caso", "count"),
            total_victims=("victimas", "sum"),
            municipio=("Municipio", "first"),
            departamento=("Departamento", "first"),
        )
        .reset_index()
    )
    inc_counts = df_mi_incidents.groupby("dane_muni")["ID Caso"].count()
    dem_counts = df_demining.groupby("dane_muni")["ID Caso"].count()
    mines_by_dane["mine_incidents"] = (
        mines_by_dane["dane_muni"].map(inc_counts).fillna(0).astype(int)
    )
    mines_by_dane["demining_count"] = (
        mines_by_dane["dane_muni"].map(dem_counts).fillna(0).astype(int)
    )

    # Match aggregated mines to GADM municipality polygons using dept+muni keys
    match_rows = []
    for _, r in mines_by_dane.iterrows():
        dept = r["departamento"]
        muni = r["municipio"]
        dane = r["dane_muni"]
        dept_k = normalize(dept)
        muni_k = normalize(muni)

        # Apply same manual corrections used in conflict matching.
        if (dept_k, muni_k) in MANUAL_MAP:
            muni_k = MANUAL_MAP[(dept_k, muni_k)]

        geo_idx = geo_lookup.get((dept_k, muni_k)) or geo_lookup.get(("", muni_k))

        if geo_idx is not None:
            # Accumulate in case multiple DANE groups point to same polygon.
            gdf.at[geo_idx, "mine_count"] = int(gdf.at[geo_idx, "mine_count"]) + int(
                r["mine_count"]
            )
            gdf.at[geo_idx, "total_victims"] = int(
                gdf.at[geo_idx, "total_victims"]
            ) + int(r["total_victims"])
            gdf.at[geo_idx, "mine_incidents"] = int(
                gdf.at[geo_idx, "mine_incidents"]
            ) + int(r["mine_incidents"])
            gdf.at[geo_idx, "demining_count"] = int(
                gdf.at[geo_idx, "demining_count"]
            ) + int(r["demining_count"])
            match_rows.append(
                {
                    "dane_muni": dane,
                    "departamento": dept,
                    "municipio": muni,
                    "mine_count": int(r["mine_count"]),
                    "total_victims": int(r["total_victims"]),
                    "mine_incidents": int(r["mine_incidents"]),
                    "demining_count": int(r["demining_count"]),
                    "matched": True,
                    "match_method": "dept+muni",
                    "matched_NAME_1": gdf.at[geo_idx, "NAME_1"],
                    "matched_NAME_2": gdf.at[geo_idx, "NAME_2"],
                }
            )
        else:
            match_rows.append(
                {
                    "dane_muni": dane,
                    "departamento": dept,
                    "municipio": muni,
                    "mine_count": int(r["mine_count"]),
                    "total_victims": int(r["total_victims"]),
                    "mine_incidents": int(r["mine_incidents"]),
                    "demining_count": int(r["demining_count"]),
                    "matched": False,
                    "match_method": "unmatched",
                    "matched_NAME_1": None,
                    "matched_NAME_2": None,
                }
            )

    report = pd.DataFrame(match_rows)
    unmatched = report[~report["matched"]].copy()
    unmatched = unmatched.sort_values(["mine_count", "total_victims"], ascending=False)
    report_path = OUT_DIR / "mine_matching_report.csv"
    unmatched_path = OUT_DIR / "unmatched_mines.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")
    unmatched.to_csv(unmatched_path, index=False, encoding="utf-8-sig")

    print(
        "Mine matching:",
        f"{int(report['matched'].sum())} of {len(report)} DANE groups matched; "
        f"unmatched mine events = {int(unmatched['mine_count'].sum())} / {len(df_mi)}",
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

    years = list(range(1994, 2025))
    desminado_anual = (
        df_demining.groupby("Año")["ID Caso"]
        .count()
        .reindex(years, fill_value=0)
    )
    incidentes_anual = (
        df_mi_incidents.groupby("Año")["ID Caso"]
        .count()
        .reindex(years, fill_value=0)
    )

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

    dem_pts = (
        df_demining[["Latitud", "Longitud", "Municipio"]]
        .dropna(subset=["Latitud", "Longitud"])
        .copy()
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
        "desminado_anual": desminado_anual.to_dict(),
        "incidentes_anual": incidentes_anual.to_dict(),
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
