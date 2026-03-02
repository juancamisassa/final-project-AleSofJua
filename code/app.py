from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import branca.colormap as bcm
import unicodedata
import re
import json

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
DERIVED_DIR = DATA_DIR / "derived-data"
st.set_page_config(
    page_title="Colombia: Conflict & Mines",
    page_icon=":colombia:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Utility functions ─────────────────────────────────────────────────

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

HITOS = {
    1998: "Demilitarized Zone",
    2002: "Plan Colombia",
    2006: "AUC Demobilization",
    2012: "Peace Negotiations",
    2016: "Peace Agreement",
}

# ── Data loading (cached) ────────────────────────────────────────────


def _load_preprocessed():
    """Load preprocessed JSON files — no geopandas, fast startup."""
    geojson_str = (DERIVED_DIR / "geojson.json").read_text(encoding="utf-8")
    country_outline_str = (
        DERIVED_DIR / "country_outline.json"
    ).read_text(encoding="utf-8")
    app_data = json.loads(
        (DERIVED_DIR / "app_data.json").read_text(encoding="utf-8")
    )

    years = list(range(1994, 2025))
    desminado_anual = pd.Series(
        {int(k): v for k, v in app_data["desminado_anual"].items()}
    ).reindex(years, fill_value=0)
    incidentes_anual = pd.Series(
        {int(k): v for k, v in app_data["incidentes_anual"].items()}
    ).reindex(years, fill_value=0)

    return {
        "geojson": geojson_str,
        "country_outline": country_outline_str,
        "desminado_anual": desminado_anual,
        "incidentes_anual": incidentes_anual,
        "top10_gap": pd.DataFrame(app_data["top10_gap"]),
        "demining_pts": pd.DataFrame(app_data["demining_pts"]),
        "stats": app_data["stats"],
    }


@st.cache_resource(show_spinner="Loading data…")
def load_data():
    if (DERIVED_DIR / "geojson.json").exists():
        return _load_preprocessed()
    st.error(
        "Preprocessed data not found. Run locally: "
        "`python code/preprocess_for_streamlit.py`"
    )
    st.stop()


# ── Map helpers ───────────────────────────────────────────────────────


def _build_choropleth(
    geojson_str, value_col, caption, colors, tooltip_alias,
    log_scale=True, show_value_in_tooltip=True, disable_interaction=False,
    show_legend=True, country_outline=None,
):
    data = json.loads(geojson_str)
    features = data["features"]

    raw_vals = [
        f["properties"][value_col]
        for f in features
        if (f["properties"].get(value_col) or 0) > 0
    ]
    if not raw_vals:
        vmax = 1.0
    elif log_scale:
        vmax = float(np.percentile([np.log1p(v) for v in raw_vals], 98))
    else:
        vmax = float(np.percentile(raw_vals, 98))
    if vmax == 0:
        vmax = 1.0

    cmap = bcm.LinearColormap(colors=colors, vmin=0, vmax=vmax, caption=caption)

    def style_fn(feature):
        val = feature["properties"].get(value_col) or 0
        if val == 0:
            return {
                "fillColor": "#f5f5f5",
                "color": "#cccccc",
                "weight": 0.4,
                "fillOpacity": 0.7,
            }
        v = np.log1p(val) if log_scale else val
        return {
            "fillColor": cmap(min(float(v), vmax)),
            "color": "#cccccc",
            "weight": 0.4,
            "fillOpacity": 0.75,
        }

    map_kwargs = dict(
        location=[4.5, -74.5],
        zoom_start=6,
        tiles="cartodbpositron",
        control_scale=not disable_interaction,
    )
    if disable_interaction:
        map_kwargs.update(
            zoom_control=False,
            scrollWheelZoom=False,
            dragging=False,
            doubleClickZoom=False,
        )
    m = folium.Map(**map_kwargs)

    tt_fields = ["NAME_2", "NAME_1"]
    tt_aliases = ["Municipality:", "Department:"]
    if show_value_in_tooltip:
        tt_fields.append(value_col)
        tt_aliases.append(f"{tooltip_alias}:")

    folium.GeoJson(
        data,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=tt_fields,
            aliases=tt_aliases,
            sticky=True,
            style="font-size:13px;",
        ),
        highlight_function=lambda x: {
            "weight": 2,
            "color": "#333",
            "fillOpacity": 0.9,
        },
    ).add_to(m)

    if show_legend:
        cmap.add_to(m)

    if country_outline:
        folium.GeoJson(
            json.loads(country_outline),
            style_function=lambda x: {
                "fillOpacity": 0,
                "color": "#333333",
                "weight": 2.5,
            },
        ).add_to(m)

    return m


# ── Pages ─────────────────────────────────────────────────────────────


def page_maps(data):
    st.markdown(
        "### Armed Conflict & Mine Density — Colombia 1994–2024"
    )

    map_choice = st.selectbox(
        "Right-side map",
        ["Mine density (by municipality)", "Total victims (by municipality)"],
        label_visibility="collapsed",
    )

    MAP_OPTS = dict(
        show_value_in_tooltip=False,
        show_legend=False,
    )

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Cumulative Armed Conflict Events by Municipality (1994–2024)**")
        m_conflict = _build_choropleth(
            data["geojson"],
            value_col="crime_count",
            caption="Conflict events",
            colors=["#ffffff", "#ffcccc", "#ff8888", "#ee4444", "#cc0000", "#8b0000"],
            tooltip_alias="Conflict events",
            **MAP_OPTS,
        )
        st_folium(m_conflict, height=620, use_container_width=True)

    with col_right:
        if map_choice.startswith("Mine density"):
            st.markdown("**Cumulative Antipersonnel Mine Incidents by Municipality (1994–2024)**")
            m_right = _build_choropleth(
                data["geojson"],
                value_col="mine_count",
                caption="Mine events",
                colors=[
                    "#ffffff", "#f0f4ff", "#ccdcff",
                    "#88aaee", "#4477cc", "#1a4e99", "#0a2d6b",
                ],
                tooltip_alias="Mine events",
                **MAP_OPTS,
            )
        else:
            st.markdown("**Cumulative Mine Victims by Municipality (1994–2024)**")
            m_right = _build_choropleth(
                data["geojson"],
                value_col="total_victims",
                caption="Total victims",
                colors=[
                    "#ffffff", "#f2e6ff", "#d9b3ff",
                    "#b366ff", "#8c1aff", "#6600cc", "#330066",
                ],
                tooltip_alias="Total victims",
                **MAP_OPTS,
            )
        st_folium(m_right, height=620, use_container_width=True)


def page_timeline(data):
    st.markdown("### Demining Operations Over Time — Colombia 1994–2024")

    years = list(range(1994, 2025))
    dem = data["desminado_anual"]
    inc = data["incidentes_anual"]

    # ── Top panel: demining line chart with two milestones ────────────
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=years,
            y=dem.values,
            mode="lines+markers",
            line=dict(color="#22aa22", width=2.5),
            marker=dict(size=6, color="#22aa22"),
            fill="tozeroy",
            fillcolor="rgba(34,170,34,0.15)",
            name="Demining operations",
            hovertemplate="Year: %{x}<br>Operations: %{y:,}<extra></extra>",
        )
    )

    MILESTONES_SHOWN = {2012: "Peace Negotiations", 2016: "Peace Agreement"}
    y_max = int(dem.max() * 1.1) or 10
    for yr, txt in MILESTONES_SHOWN.items():
        fig.add_vline(
            x=yr, line_dash="dot", line_color="#888888", line_width=1,
        )
        fig.add_annotation(
            x=yr,
            y=y_max,
            text=txt,
            showarrow=False,
            font=dict(size=10, color="#444444"),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#bbbbbb",
            borderwidth=1,
            borderpad=4,
            yanchor="top",
        )

    fig.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=60, r=30, t=40, b=60),
        xaxis=dict(
            title="Year",
            dtick=2,
            range=[1993.5, 2024.5],
            tickangle=-45,
        ),
        yaxis=dict(title="Demining operations", color="#22aa22"),
        legend=dict(
            x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#cccccc", borderwidth=1,
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── Bottom panel: 100 % stacked bar (incidents vs demining) ──────
    st.markdown("**Proportion of mine events: incidents vs demining**")

    total = dem.values + inc.values
    safe_total = np.where(total > 0, total, 1)
    pct_inc = inc.values / safe_total * 100
    pct_dem = dem.values / safe_total * 100

    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(
            x=years, y=pct_inc, name="Mine incidents",
            marker_color="#cc5500",
            hovertemplate="Year %{x}<br>Incidents: %{y:.1f}%<extra></extra>",
        )
    )
    fig2.add_trace(
        go.Bar(
            x=years, y=pct_dem, name="Demining operations",
            marker_color="#22aa22",
            hovertemplate="Year %{x}<br>Demining: %{y:.1f}%<extra></extra>",
        )
    )
    fig2.update_layout(
        barmode="stack",
        template="plotly_white",
        height=260,
        margin=dict(l=60, r=30, t=10, b=50),
        xaxis=dict(dtick=2, range=[1993.5, 2024.5], tickangle=-45, title="Year"),
        yaxis=dict(title="% of mine events", range=[0, 105]),
        legend=dict(
            x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#cccccc", borderwidth=1,
        ),
    )

    st.plotly_chart(fig2, use_container_width=True)


def page_priority(data):
    st.markdown(
        "### Demining Priority: Mine Incidents minus Demining — Colombia 1994–2024"
    )
    st.caption(
        "Municipalities with the largest gap between mine incidents and demining operations. "
        "The map shows the raw difference (incidents − demining) per municipality."
    )

    col_left, col_right = st.columns([2, 3])

    with col_left:
        st.markdown("**Top 10 municipalities (incidents − demining)**")
        top10 = data["top10_gap"]

        fig_bar = go.Figure(
            go.Bar(
                y=top10["NAME_2"],
                x=top10["incidents_minus_demining"],
                orientation="h",
                marker_color="#c45a00",
                marker_line_color="#8b3a00",
                marker_line_width=1,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Gap: %{x}<br>"
                    "<extra></extra>"
                ),
            )
        )
        fig_bar.update_layout(
            template="plotly_white",
            height=520,
            margin=dict(l=10, r=20, t=10, b=40),
            xaxis=dict(title="Mine incidents − demining", showticklabels=False),
            yaxis=dict(automargin=True, tickfont=dict(size=12)),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.markdown("**Demining Gap Index: Mine Incidents minus Demining Operations**")

        m_gap = _build_choropleth(
            data["geojson"],
            value_col="gap_raw",
            caption="Incidents − demining",
            colors=[
                "#fff5eb", "#ffddb8", "#ffc078",
                "#ff9f40", "#e87500", "#c45a00", "#8b3a00",
            ],
            tooltip_alias="Gap (incidents − demining)",
            show_legend=False,
        )

        dem_group = folium.FeatureGroup(name="Demining operations")
        for _, pt in data["demining_pts"].iterrows():
            folium.CircleMarker(
                location=[pt["Latitud"], pt["Longitud"]],
                radius=4,
                color="#115511",
                fill=True,
                fill_color="#22aa22",
                fill_opacity=0.8,
                weight=0.6,
                tooltip=f"Demining — {pt['Municipio']}",
            ).add_to(dem_group)
        dem_group.add_to(m_gap)
        folium.LayerControl(collapsed=False).add_to(m_gap)

        st_folium(m_gap, height=620, use_container_width=True)


# ── Sidebar & routing ─────────────────────────────────────────────────

st.sidebar.title("Colombia: Conflict & Mines")
st.sidebar.markdown("---")

PAGES = {
    "Conflict & Mine Maps": page_maps,
    "Demining Timeline": page_timeline,
    "Priority Analysis": page_priority,
}

selection = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Sources: [UCDP GED v25.1](https://ucdp.uu.se/downloads/) · "
    "[Descontamina Colombia](http://www.accioncontraminas.gov.co/)"
)

data = load_data()
PAGES[selection](data)
