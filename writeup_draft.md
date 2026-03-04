# Conflict & Demining Policy in Colombia — Final Project Write-up (Draft)

**Group 8:** Alejandra Patiño, Sofía Linares, Juan Camisassa  
**Lecture section:** [Day/time]  
**GitHub:** [usernames]

---

## 1. Introduction and Context

Colombia has experienced prolonged armed conflict and ranks among the countries with the highest number of recorded conflict events according to the UCDP Georeferenced Event Dataset (GED). Beyond conflict events, Colombia faces extensive antipersonnel landmine contamination. By 2018, it was estimated to be among the top 10 countries worldwide with the highest number of victims of antipersonnel mines and explosive remnants of war (Landmine Monitor, 2018).

This project examines the spatial overlap between armed conflict and landmine incidents at the municipal level, and evaluates whether post-2016 demining policy has targeted the most affected areas. Our goal is to build a data-driven prioritization tool for demining policy allocation.

---

## 2. Research Questions

1. Are conflict events and landmine incidents spatially correlated at the municipal level?
2. Has post-2016 demining policy targeted the most affected municipalities?

We aim to provide a practical prioritization framework for policymakers, rather than to establish causal relationships.

---

## 3. Data

We use three data sources:

- **UCDP Georeferenced Event Dataset (GED):** Geo-coded events of organized violence (at least one fatality, state or armed group involved). We use events in Colombia from 1994–2024.
- **CasosMI (Descontamina Colombia / National Center for Historical Memory):** Public database of landmine and explosive device incidents and victims (1953–2025). We filter for mine-related events and aggregate by municipality.
- **GADM v4.1 (Colombia, Level 2):** Administrative boundaries for Colombian municipalities, used as the geographic base for our maps.

**Data integration:** We merged the three datasets by municipality. We normalized municipality names (lowercase, remove accents and special characters) and matched them to GADM polygons using a lookup dictionary. For known discrepancies (e.g., Bogotá vs. Bogotá DC), we applied manual mappings. Each municipality polygon was assigned conflict counts and mine-related counts from both sources.

---

## 4. Approach and Coding

**Data wrangling:** All processing is done in our `.qmd` and preprocessing scripts. We aggregate GEDEvent and CasosMI by municipality, join to GADM geometries, and compute counts for conflict events, mine incidents, mine victims, and demining operations.

**Static visualizations:** We created at least two static plots using GeoPandas/Altair, including at least one spatial visualization (choropleth maps).

**Streamlit app:** Our dashboard has three pages: (1) Conflict & Mine Maps, showing choropleth maps of conflict events, mine incidents, and mine victims by municipality; (2) Demining Timeline, showing demining operations over time with milestones (Peace Negotiations 2012, Peace Agreement 2016); (3) Priority Analysis, showing the gap index (incidents minus demining) and top 10 municipalities. For deployment on Streamlit Community Cloud, we preprocess data locally to avoid heavy geopandas dependencies at runtime.

---

## 5. Results

### Static plots (same as dashboard maps 1 & 2)

**Figure 1: Cumulative Armed Conflict Events by Municipality (1994–2024)**  
*File: `code/mapa_conflicto_dashboard_static.png`*

[Brief description: spatial distribution of armed conflict events; relates to RQ1.]

**Figure 2: Cumulative Antipersonnel Mine Incidents by Municipality (1994–2024)**  
*File: `code/mapa_minas_dashboard_static.png`*

[Brief description: spatial distribution of mine incidents; relates to RQ1.]

---

### Streamlit Dashboard — Link: [Streamlit Community Cloud URL]

The dashboard mixes **interactive** and **fixed** elements:

- **Conflict & Mine Maps (interactive):** Side-by-side choropleths with zoom, pan, and hover tooltips. Users can toggle between mine incidents and mine victims for the right-hand map. We use a **logarithmic color scale**: each municipality's count is transformed as log(1 + count) before mapping to color. Without this, a few municipalities with very high counts would dominate the color range and most areas would appear nearly identical; the log scale compresses the range so that low, medium, and high counts all receive distinct colors, making spatial variation visible across the full distribution.

- **Demining Timeline (fixed charts):** A line chart of demining operations over time, with vertical markers for the 2016 Peace Agreement and 2012 Peace Negotiations, and a stacked bar chart showing the proportion of mine events that are incidents vs. demining operations by year.

- **Priority Analysis (interactive map + fixed chart):** An interactive choropleth of the gap index (mine incidents minus demining operations), overlaid with demining operation locations, plus a fixed horizontal bar chart of the top 10 municipalities with the largest gap.

---

## 6. Peace Agreement and Demining Policy

The 2016 Peace Agreement marked a policy shift by institutionalizing demining policy. Demining activity increases sharply after 2016, reflecting both policy prioritization and improved discovery and reporting.

Demining increases economic growth by enabling access to essential infrastructure and new markets (Chiovelli, Michalopoulos, & Papaioannou, 2019); opening opportunities for the productive exploitation of natural resources (Gunawardana, Tantrigoda, & Kumara, 2016); and facilitating productive activities and supporting land restitution processes (Cabrera & Pachón, 2017). Our prioritization framework aims to support more efficient allocation of demining resources to the most affected municipalities.

---

## 7. Policy Implications and Limitations

Our gap index (incidents minus demining) provides a simple, descriptive prioritization tool. Large positive values indicate potentially under-served municipalities where demining efforts may need to be intensified.

**Limitations:** This analysis is descriptive. We do not establish causal relationships between conflict, landmines, and demining policy. The gap index does not account for differences in terrain, accessibility, or capacity constraints across municipalities.

---

## 8. Conclusion

We combine UCDP conflict data, CasosMI mine incident data, and GADM administrative boundaries to visualize the spatial distribution of conflict and landmines in Colombia and to construct a gap-based prioritization index for demining policy. The 2016 Peace Agreement coincides with a sharp increase in demining activity. Our dashboard serves as a practical tool for policymakers to identify municipalities where the gap between mine incidents and demining operations remains largest.

---

## References

- Cabrera, M., & Pachón, M. (2017). [Full citation]
- Chiovelli, S., Michalopoulos, S., & Papaioannou, E. (2019). [Full citation]
- Gunawardana, P. J., Tantrigoda, R. A., & Kumara, P. A. (2016). [Full citation]
- Landmine Monitor (2018). [Full citation]
