"""
Export static PNG versions of dashboard maps and charts.
Same titles and styling as the Streamlit app. Run: python code/export_dashboard_maps_static.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import geopandas as gpd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
DERIVED_DIR = DATA_DIR / "derived-data"
OUT_DIR = BASE_DIR

# Dashboard colors (from app.py)
CONFLICT_COLORS = ["#ffffff", "#ffcccc", "#ff8888", "#ee4444", "#cc0000", "#8b0000"]
MINE_COLORS = ["#ffffff", "#f0f4ff", "#ccdcff", "#88aaee", "#4477cc", "#1a4e99", "#0a2d6b"]
GAP_COLORS = ["#fff5eb", "#ffddb8", "#ffc078", "#ff9f40", "#e87500", "#c45a00", "#8b3a00"]

# Dashboard titles
TITLE_CONFLICT = "Cumulative Armed Conflict Events by Municipality (1994–2024)"
TITLE_MINE = "Cumulative Antipersonnel Mine Incidents by Municipality (1994–2024)"


def plot_choropleth(gdf, value_col, colors, title, out_path):
    gdf = gdf.copy()
    gdf["val_log"] = np.where(gdf[value_col] > 0, np.log1p(gdf[value_col]), 0)

    cmap = mcolors.LinearSegmentedColormap.from_list("custom", colors, N=256)

    fig, ax = plt.subplots(1, 1, figsize=(10, 14), facecolor="white")
    ax.set_facecolor("white")

    gdf[gdf[value_col] == 0].plot(
        ax=ax, color="#f5f5f5", edgecolor="#cccccc", linewidth=0.2
    )

    gdf_with = gdf[gdf[value_col] > 0]
    if len(gdf_with) > 0:
        vmax = gdf_with["val_log"].quantile(0.98)
        gdf_with.plot(
            ax=ax, column="val_log", cmap=cmap,
            edgecolor="#cccccc", linewidth=0.2,
            vmin=0, vmax=vmax, legend=False
        )
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(vmin=0, vmax=vmax))
        sm._A = []
        cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02, aspect=30)
        tick_vals = np.linspace(0, vmax, 6)
        tick_labs = [f"{int(np.expm1(v))}" for v in tick_vals]
        cbar.set_ticks(tick_vals)
        cbar.set_ticklabels(tick_labs)
        cbar.set_label("Count", fontsize=11, color="#333333", labelpad=10)
        cbar.ax.tick_params(colors="#333333", labelsize=9)

    ax.set_title(title, fontsize=16, fontweight="bold", color="#222222", pad=15)
    ax.set_axis_off()
    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"Saved {out_path}")


def main():
    geojson_path = DERIVED_DIR / "geojson.json"
    if not geojson_path.exists():
        print("Run preprocess_for_streamlit.py first to generate derived-data/geojson.json")
        return

    gdf = gpd.read_file(geojson_path)

    plot_choropleth(
        gdf, "crime_count", CONFLICT_COLORS,
        TITLE_CONFLICT,
        OUT_DIR / "mapa_conflicto_dashboard_static.png",
    )
    plot_choropleth(
        gdf, "mine_count", MINE_COLORS,
        TITLE_MINE,
        OUT_DIR / "mapa_minas_dashboard_static.png",
    )

    # Load app_data for timeline and priority
    app_data = json.loads((DERIVED_DIR / "app_data.json").read_text(encoding="utf-8"))
    years = list(range(1994, 2025))
    dem = pd.Series({int(k): v for k, v in app_data["desminado_anual"].items()}).reindex(years, fill_value=0)
    inc = pd.Series({int(k): v for k, v in app_data["incidentes_anual"].items()}).reindex(years, fill_value=0)
    top10 = pd.DataFrame(app_data["top10_gap"])
    dem_pts = pd.DataFrame(app_data["demining_pts"])

    # Demining timeline: line chart
    fig1, ax1 = plt.subplots(figsize=(12, 5), facecolor="white")
    ax1.fill_between(years, dem.values, alpha=0.15, color="#22aa22")
    ax1.plot(years, dem.values, color="#22aa22", linewidth=2.5, marker="o", markersize=5, label="Demining operations")
    y_max = dem.max() * 1.15
    ax1.set_ylim(0, y_max)
    for yr, txt in [(2012, "Peace Negotiations"), (2016, "Peace Agreement")]:
        ax1.axvline(yr, color="#888888", linestyle=":", linewidth=1)
        ax1.annotate(txt, xy=(yr, y_max * 0.92), fontsize=10, ha="center", va="top",
                     bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85, edgecolor="#bbbbbb"))
    ax1.set_xlabel("Year", fontsize=12)
    ax1.set_ylabel("Demining operations", fontsize=12, color="#22aa22")
    ax1.set_xlim(1993.5, 2024.5)
    ax1.set_xticks(range(1994, 2025, 2))
    ax1.tick_params(axis="x", rotation=45)
    ax1.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#cccccc")
    ax1.set_title("Demining Operations Over Time — Colombia 1994–2024", fontsize=14, fontweight="bold", pad=20)
    plt.tight_layout()
    fig1.savefig(OUT_DIR / "grafica_demining_timeline.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print("Saved grafica_demining_timeline.png")

    # Demining timeline: stacked bar (incidents vs demining %)
    total = dem.values + inc.values
    safe = np.where(total > 0, total, 1)
    pct_inc = inc.values / safe * 100
    pct_dem = dem.values / safe * 100
    fig2, ax2 = plt.subplots(figsize=(12, 4), facecolor="white")
    ax2.bar(years, pct_inc, color="#cc5500", label="Mine incidents")
    ax2.bar(years, pct_dem, bottom=pct_inc, color="#22aa22", label="Demining operations")
    ax2.set_xlabel("Year", fontsize=12)
    ax2.set_ylabel("% of mine events", fontsize=12)
    ax2.set_xlim(1993.5, 2024.5)
    ax2.set_ylim(0, 105)
    ax2.set_xticks(range(1994, 2025, 2))
    ax2.tick_params(axis="x", rotation=45)
    ax2.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#cccccc")
    ax2.set_title("Proportion of mine events: incidents vs demining", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig2.savefig(OUT_DIR / "grafica_demining_proporciones.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print("Saved grafica_demining_proporciones.png")

    # Priority: horizontal bar chart
    top10_sorted = top10.sort_values("incidents_minus_demining", ascending=True)
    fig3, ax3 = plt.subplots(figsize=(8, 6), facecolor="white")
    ax3.barh(top10_sorted["NAME_2"], top10_sorted["incidents_minus_demining"],
             color="#c45a00", edgecolor="#8b3a00", linewidth=1)
    ax3.set_xlabel("Mine incidents − demining", fontsize=12)
    ax3.set_title("Top 10 municipalities (incidents − demining)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig3.savefig(OUT_DIR / "grafica_priority_top10.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print("Saved grafica_priority_top10.png")

    # Priority: gap choropleth map with demining points
    gdf["gap_log"] = np.where(gdf["gap_raw"] > 0, np.log1p(gdf["gap_raw"]), 0)
    cmap_gap = mcolors.LinearSegmentedColormap.from_list("gap", GAP_COLORS, N=256)
    fig4, ax4 = plt.subplots(1, 1, figsize=(10, 14), facecolor="white")
    ax4.set_facecolor("white")
    gdf[gdf["gap_raw"] == 0].plot(ax=ax4, color="#f5f5f5", edgecolor="#cccccc", linewidth=0.2)
    gdf_gap = gdf[gdf["gap_raw"] > 0]
    if len(gdf_gap) > 0:
        vmax_g = gdf_gap["gap_log"].quantile(0.98)
        gdf_gap.plot(ax=ax4, column="gap_log", cmap=cmap_gap, edgecolor="#cccccc", linewidth=0.2, vmin=0, vmax=vmax_g, legend=False)
        sm_g = plt.cm.ScalarMappable(cmap=cmap_gap, norm=mcolors.Normalize(vmin=0, vmax=vmax_g))
        sm_g._A = []
        cbar = fig4.colorbar(sm_g, ax=ax4, fraction=0.025, pad=0.02, aspect=30)
        cbar.set_label("Incidents − demining", fontsize=11)
    ax4.scatter(dem_pts["Longitud"], dem_pts["Latitud"], s=25, c="#22aa22", edgecolors="#115511",
                linewidths=0.6, zorder=5, label="Demining operations")
    ax4.set_title("Demining Gap Index: Mine Incidents minus Demining Operations", fontsize=14, fontweight="bold")
    ax4.legend(loc="lower left", fontsize=10)
    ax4.set_axis_off()
    plt.tight_layout()
    fig4.savefig(OUT_DIR / "mapa_priority_gap.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print("Saved mapa_priority_gap.png")


if __name__ == "__main__":
    main()
