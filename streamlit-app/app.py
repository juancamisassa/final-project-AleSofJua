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
    accidentes_map_anual = pd.Series(
        {int(k): v for k, v in app_data.get("accidentes_map_anual", app_data["incidentes_anual"]).items()}
    ).reindex(years, fill_value=0)

    desminado_por_depto = {}
    for dept, yearly in app_data.get("desminado_por_depto", {}).items():
        desminado_por_depto[dept] = pd.Series(
            {int(k): v for k, v in yearly.items()}
        ).reindex(years, fill_value=0)

    accidentes_map_por_depto = {}
    for dept, yearly in app_data.get("accidentes_map_por_depto", {}).items():
        accidentes_map_por_depto[dept] = pd.Series(
            {int(k): v for k, v in yearly.items()}
        ).reindex(years, fill_value=0)

    return {
        "geojson": geojson_str,
        "country_outline": country_outline_str,
        "desminado_anual": desminado_anual,
        "accidentes_map_anual": accidentes_map_anual,
        "incidentes_anual": incidentes_anual,
        "desminado_por_depto": desminado_por_depto,
        "accidentes_map_por_depto": accidentes_map_por_depto,
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
        "`python preprocessing.py`"
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

    # Sanitize numeric properties to avoid numpy/NaN issues with folium/branca
    for f in features:
        props = f["properties"]
        if value_col in props:
            v = props[value_col]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                props[value_col] = 0.0
            else:
                props[value_col] = float(v)

    if log_scale:
        raw_vals = [
            f["properties"][value_col]
            for f in features
            if (f["properties"].get(value_col) or 0) > 0
        ]
    else:
        raw_vals = [
            f["properties"][value_col]
            for f in features
            if f["properties"].get(value_col) is not None
            and not (isinstance(f["properties"][value_col], float) and np.isnan(f["properties"][value_col]))
        ]
    if not raw_vals:
        vmin, vmax = 0.0, 1.0
    elif log_scale:
        vmin = 0.0
        vmax = float(np.percentile([np.log1p(v) for v in raw_vals], 98))
        if vmax == 0:
            vmax = 1.0
    else:
        vmin = float(np.percentile(raw_vals, 2))
        vmax = float(np.percentile(raw_vals, 98))
        if vmax <= vmin or (vmax - vmin) < 1e-6:
            vmin, vmax = vmin - 0.5, vmax + 0.5

    cmap = bcm.LinearColormap(colors=colors, vmin=vmin, vmax=vmax, caption=caption)

    def style_fn(feature):
        val = feature["properties"].get(value_col)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            val = 0
        if log_scale and val == 0:
            return {
                "fillColor": "#f5f5f5",
                "color": "#cccccc",
                "weight": 0.4,
                "fillOpacity": 0.7,
            }
        v = np.log1p(val) if log_scale else float(val)
        v_clipped = min(max(v, vmin), vmax) if not log_scale else min(float(v), vmax)
        v_clipped = float(v_clipped)  # Ensure Python float for branca
        return {
            "fillColor": cmap(v_clipped),
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


def _build_priority_map_plotly(geojson_str, value_col="priority_idx"):
    """Build priority map with Plotly (more reliable than Folium on Streamlit Cloud)."""
    data = json.loads(geojson_str)
    features = data["features"]

    locations = []
    z_vals = []
    hover_names = []
    for f in features:
        props = f["properties"]
        n1 = props.get("NAME_1", "")
        n2 = props.get("NAME_2", "")
        locations.append(f"{n1}|{n2}")
        hover_names.append(f"{n2} ({n1})")
        v = props.get(value_col)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            z_vals.append(0.0)
        else:
            z_vals.append(float(v))

    for i, f in enumerate(features):
        f["properties"]["_id"] = locations[i]

    # Use 2nd–98th percentile: intermediate between full range (flat) and 5–95 (compressed)
    vmin = float(np.percentile(z_vals, 2))
    vmax = float(np.percentile(z_vals, 98))
    if vmax <= vmin or (vmax - vmin) < 1e-6:
        vmin, vmax = float(np.min(z_vals)) - 0.5, float(np.max(z_vals)) + 0.5

    fig = go.Figure(go.Choroplethmapbox(
        geojson=data,
        locations=locations,
        featureidkey="properties._id",
        z=z_vals,
        customdata=np.array(hover_names)[:, np.newaxis],
        colorscale=[
            [0, "#fff5eb"], [0.2, "#ffddb8"], [0.4, "#ffc078"],
            [0.6, "#ff9f40"], [0.8, "#e87500"], [1, "#8b3a00"],
        ],
        zmin=vmin,
        zmax=vmax,
        marker_line_width=0.5,
        marker_opacity=0.75,
        colorbar=dict(
            title="",
            thickness=15,
            len=0.6,
            tickvals=[vmin, vmax],
            ticktext=["Low priority", "High priority"],
        ),
        hovertemplate="<b>%{customdata[0]}</b><br>Priority: %{z:.2f}<extra></extra>",
    ))

    fig.update_layout(
        mapbox=dict(
            style="carto-positron",
            center=dict(lat=4.5, lon=-74.5),
            zoom=5,
            bounds={"west": -80, "east": -66, "south": -5, "north": 13},
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=620,
    )

    return fig


# ── Pages ─────────────────────────────────────────────────────────────


def page_maps(data):
    st.markdown(
        "### Armed Conflict & Mine Events — Colombia 1994–2024"
    )

    map_choice = st.selectbox(
        "Right-side map",
        [
            "Cumulative Mine Accidents by Municipality (1994–2024)",
            "Cumulative Mine Victims by Municipality (1994–2024)",
        ],
        label_visibility="collapsed",
    )

    MAP_OPTS = dict(
        show_value_in_tooltip=True,
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
        st.caption("*Source: UCDP GED v25.1*")

    with col_right:
        if map_choice.startswith("Cumulative Mine Accidents"):
            st.markdown("**Cumulative Mine Accidents by Municipality (1994–2024)**")
            m_right = _build_choropleth(
                data["geojson"],
                value_col="mine_incidents",
                caption="Accidentes MAP",
                colors=[
                    "#ffffff", "#f0f4ff", "#ccdcff",
                    "#88aaee", "#4477cc", "#1a4e99", "#0a2d6b",
                ],
                tooltip_alias="MAP accidents",
                **MAP_OPTS,
            )
        else:
            st.markdown("**Cumulative Mine Victims by Municipality (1994–2024)**")
            m_right = _build_choropleth(
                data["geojson"],
                value_col="total_victims",
                caption="Mine victims",
                colors=[
                    "#ffffff", "#f2e6ff", "#d9b3ff",
                    "#b366ff", "#8c1aff", "#6600cc", "#330066",
                ],
                tooltip_alias="Mine victims",
                **MAP_OPTS,
            )
        st_folium(m_right, height=620, use_container_width=True)
        st.caption(
            "*Sources: AICMA Open Database of Anti-Personnel Mines (MAP); "
            "Victims: Centro Nacional de Memoria Histórica, CasosMI*"
        )


def page_timeline(data):
    # ── Filters ───────────────────────────────────────────────────────
    dept_map = data.get("desminado_por_depto", {})
    dept_options = sorted(dept_map.keys())

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        dept_choice = st.selectbox(
            "Department",
            ["All Colombia"] + dept_options,
        )
    with col_f2:
        yr_min, yr_max = st.slider(
            "Year range",
            min_value=1994,
            max_value=2024,
            value=(1994, 2024),
        )

    label = dept_choice if dept_choice != "All Colombia" else "Colombia"
    st.markdown(f"### Demining and Mine Incidents — {label} ({yr_min}–{yr_max})")

    all_years = list(range(1994, 2025))
    if dept_choice == "All Colombia":
        dem_full = data["desminado_anual"]
        map_ev_full = data["accidentes_map_anual"]
    else:
        dem_full = dept_map.get(
            dept_choice, pd.Series(dtype=int)
        ).reindex(all_years, fill_value=0)
        map_ev_full = data.get("accidentes_map_por_depto", {}).get(
            dept_choice, pd.Series(dtype=int)
        ).reindex(all_years, fill_value=0)

    years = list(range(yr_min, yr_max + 1))
    dem = dem_full.loc[yr_min:yr_max]
    map_ev = map_ev_full.loc[yr_min:yr_max]
    inc = map_ev

    # ── Line chart: desminado + accidentes MAP por año ─────────────────
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
            name="Demining",
            hovertemplate="Year: %{x}<br>Demining: %{y:,}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=map_ev.values,
            mode="lines+markers",
            line=dict(color="#cc5500", width=2.5),
            marker=dict(size=6, color="#cc5500"),
            name="Mine incidents",
            hovertemplate="Year: %{x}<br>Mine incidents: %{y:,}<extra></extra>",
        )
    )

    MILESTONES_SHOWN = {2012: "Peace Negotiations", 2016: "Peace Agreement"}
    y_max = int(max(dem.max(), map_ev.max()) * 1.1) or 10
    for yr, txt in MILESTONES_SHOWN.items():
        if yr_min <= yr <= yr_max:
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
            range=[yr_min - 0.5, yr_max + 0.5],
            tickangle=-45,
        ),
        yaxis=dict(title="Event count"),
        legend=dict(
            x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#cccccc", borderwidth=1,
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── Bottom panel: proportion demining vs MAP accidents ───────────
    st.markdown("**Proportion of events: incidents vs demining**")

    total = dem.values + inc.values
    safe_total = np.where(total > 0, total, 1)
    pct_inc = inc.values / safe_total * 100
    pct_dem = dem.values / safe_total * 100

    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(
            x=years, y=pct_inc,
            name="Mine incidents",
            marker_color="#cc5500",
            hovertemplate="Year %{x}<br>Incidents: %{y:.1f}%<extra></extra>",
        )
    )
    fig2.add_trace(
        go.Bar(
            x=years, y=pct_dem,
            name="Demining",
            marker_color="#22aa22",
            hovertemplate="Year %{x}<br>Demining: %{y:.1f}%<extra></extra>",
        )
    )
    fig2.update_layout(
        barmode="stack",
        template="plotly_white",
        height=260,
        margin=dict(l=60, r=30, t=10, b=50),
        xaxis=dict(dtick=2, range=[yr_min - 0.5, yr_max + 0.5], tickangle=-45, title="Year"),
        yaxis=dict(title="% of mine events", range=[0, 105]),
        legend=dict(
            x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#cccccc", borderwidth=1,
        ),
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.caption("*Source: AICMA Open Database of Anti-Personnel Mines (MAP)*")


def page_priority(data):
    st.markdown(
        "### Demining Priority Index — Colombia 1994–2024"
    )

    col_left, col_right = st.columns([2, 3])

    with col_left:
        top_all = data["top10_gap"]
        priority_col = "priority_idx" if "priority_idx" in top_all.columns else "incidents_minus_demining"
        n_munis = st.slider("Number of municipalities", min_value=5, max_value=len(top_all), value=10)
        top_n = top_all.sort_values(priority_col, ascending=True).tail(n_munis)
        st.markdown(f"**Top {n_munis} municipalities by priority index**")

        fig_bar = go.Figure(
            go.Bar(
                y=top_n["NAME_2"],
                x=top_n[priority_col],
                orientation="h",
                marker_color="#c45a00",
                marker_line_color="#8b3a00",
                marker_line_width=1,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Priority index: %{x:.2f}<br>"
                    "<extra></extra>"
                ),
            )
        )
        fig_bar.update_layout(
            template="plotly_white",
            height=600,
            margin=dict(l=10, r=20, t=10, b=40),
            xaxis=dict(title="Priority index", showticklabels=False),
            yaxis=dict(automargin=True, tickfont=dict(size=12)),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.markdown("**Priority Index**")
        st.markdown(
            "Z(conflict) + Z(mine incidents) − Z(demining). "
            "Higher values indicate municipalities with more conflict "
            "and mine incidents relative to demining activity.",
        )

        fig_priority = _build_priority_map_plotly(
            data["geojson"],
            value_col="priority_idx",
        )
        st.plotly_chart(fig_priority, use_container_width=True)


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
    "**Sources:** [UCDP GED](https://ucdp.uu.se/downloads/) · "
    "[Descontamina Colombia](http://www.accioncontraminas.gov.co/) · "
    "[AICMA Datos Abiertos](https://www.accioncontraminas.gov.co/Estadisticas/datos-abiertos) · "
    "[Victims dataset — Centro Nacional de Memoria Histórica](https://www.centrodememoriahistorica.gov.co/)"
)

data = load_data()
PAGES[selection](data)
