# earlier streamlit version , new version in app.py
import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point
from geo_retriever import get_spatial_context, load_all_layers
import time

if "analyze_clicked" not in st.session_state:
    st.session_state.analyze_clicked = False

# --------------------------------------------
# CONFIGURATION
# --------------------------------------------
st.set_page_config(page_title="GeoRAG Spatial Visualizer", layout="wide")

st.title("🗺️ GeoMind Spatial Visualizer")
st.caption("Visualize nearby spatial features (forest, aquifer, reservoir, etc.) around any location.")

# --------------------------------------------
# LOAD DATA
# --------------------------------------------

# LOAD DATA (CACHED)
st.sidebar.header("Settings")

@st.cache_resource(show_spinner=False)
def get_layers_cached():
    return load_all_layers()

layers = get_layers_cached()



buffer_km = st.sidebar.slider("Buffer distance (km)", 10, 100, 50, step=10)
query = st.text_input("Enter a location (e.g., 'Kota, Rajasthan')", "Kota, Rajasthan")

if st.button("Analyze"):
    st.session_state.analyze_clicked = True

if st.session_state.analyze_clicked:
    with st.spinner("Retrieving spatial data..."):
        spatial_result = get_spatial_context(query, all_layers=layers)
        lat, lon = spatial_result.get("latitude"), spatial_result.get("longitude")

        if "error" in spatial_result:
            st.error(spatial_result["error"])
        else:
            st.success(f"Showing results near **{spatial_result['location']}**")

            # --------------------------------------------
            # BASE MAP
            # --------------------------------------------
            m = folium.Map(location=[lat, lon], zoom_start=7)

            # Add the query point
            folium.Marker(
                location=[lat, lon],
                popup=f" Query: {query}",
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)

            # --------------------------------------------
            # PLOT NEARBY FEATURES
            # --------------------------------------------
            color_map = {
                "forest_cover": "green",
                "aquifers": "blue",
                "reservoir": "purple",
                "structure": "orange",
                "inter_basin": "cadetblue"
            }

            for layer_name, gdf in layers.items():
                try:
                    gdf_proj = gdf.to_crs(epsg=3857)
                    point_proj = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
                    nearby = gdf_proj[gdf_proj.geometry.distance(point_proj) <= buffer_km * 1000]

                    if not nearby.empty:
                        # Back to WGS84 for Folium
                        nearby = nearby.to_crs(epsg=4326)

                        for _, row in nearby.iterrows():
                            geom = row.geometry
                            color = color_map.get(layer_name, "gray")

                            if geom.geom_type == "Polygon" or geom.geom_type == "MultiPolygon":
                                folium.GeoJson(
                                    geom,
                                    style_function=lambda x, col=color: {"color": col, "weight": 1.5, "fillOpacity": 0.2},
                                    popup=f"{layer_name.upper()} — {list(row.items())[:5]}",
                                ).add_to(m)
                            elif geom.geom_type == "Point":
                                folium.CircleMarker(
                                    location=[geom.y, geom.x],
                                    radius=4,
                                    color=color,
                                    fill=True,
                                    fill_color=color,
                                    popup=f"{layer_name.upper()} — {list(row.items())[:5]}",
                                ).add_to(m)
                            elif geom.geom_type == "LineString":
                                folium.PolyLine(
                                    locations=[(y, x) for x, y in geom.coords],
                                    color=color,
                                    weight=2,
                                    popup=f"{layer_name.upper()} — {list(row.items())[:5]}",
                                ).add_to(m)
                except Exception as e:
                    st.warning(f"Error plotting {layer_name}: {e}")

            # --------------------------------------------
            # DISPLAY MAP
            # -------------------------------------------- 
            time.sleep(0.1)
            st_folium(m, width=900, height=600, returned_objects=[], key="map_display")

            # Show textual summary
            from geo_retriever import summarize_spatial_context
            st.markdown("### Spatial Summary")
            st.markdown(summarize_spatial_context(spatial_result))
