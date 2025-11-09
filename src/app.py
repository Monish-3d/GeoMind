import streamlit as st
from fusion_engine import fuse_query
from geo_retriever import load_all_layers
from geo_map_utils import create_base_map, add_layers_to_map
from streamlit_folium import st_folium

st.set_page_config(page_title="GeoMind", layout="wide")

st.title("🌍 GeoMind — Environmental & Spatial Intelligence System")

# load heavy layers once and keep in session_state
@st.cache_resource(show_spinner=False)
def _get_layers_cached():
    return load_all_layers()

if "layers" not in st.session_state:
    st.session_state.layers = _get_layers_cached()
layers = st.session_state.layers

# Sidebar controls----------------------------------------------------------------
with st.sidebar:
    st.header("Options")
    buffer_km = st.slider("Map buffer (km) for visualization", 10, 200, 50, step=5)
    k = st.slider("Top-K text chunks (RAG)", 3, 15, 8)
    source = st.selectbox("Text source filter", ["Any", "MoEFCC", "IMD"])
    source = None if source == "Any" else source
    yr_min = st.number_input("Year start", 2005, 2025, 2010)
    yr_max = st.number_input("Year end", 2005, 2025, 2020)
    use_years = st.checkbox("Force year range filter", value=False)

# Query area and action button------------------------------------------------------------------------------------
query = st.text_input("Ask a question like 'How has forest cover near Chennai changed between 2010 and 2020?' ", "")
if st.button(" Analyze") and query.strip():
    yr_range = (int(yr_min), int(yr_max)) if use_years else None
    with st.spinner("Thinking with maps and reports..."):
        result = fuse_query(query, k=k, source=source, year_range=yr_range)
    st.session_state.last_result = result

# Render last result in two-column layout: left = text, right = map
out = st.session_state.get("last_result")
if out:
    col_left, col_right = st.columns([2, 1])

    # LEFT: Answer + summary + sources + debug
    with col_left:
        st.subheader("GeoMind Response")
        # keep answer readable (it is produced by the LLM)
        st.write(out["answer"])

        st.markdown("### Spatial Summary")
        st.markdown(out["spatial_summary"] or "No spatial summary available.")

        st.markdown("### Sources")
        for s in out["sources"]:
            st.write("•", s)

        with st.expander("Show top retrieved text chunks"):
            for d in out["text_chunks"][:8]:
                meta = d.get("metadata", {})
                st.markdown(f"**{meta.get('source')} · {meta.get('filename')} · {meta.get('year')} · chunk {meta.get('chunk_id')}**")
                st.write(d.get("content"))

        # with st.expander("Debug: Spatial raw"):
        #     st.json(out["spatial_raw"])

    # RIGHT: Map (keeps map stable on interaction)
    with col_right:
        st.subheader("Map")
        sr = out.get("spatial_raw", {})
        if "latitude" in sr and "longitude" in sr:
            lat, lon = sr["latitude"], sr["longitude"]
            m = create_base_map(lat, lon, zoom=8)
            m = add_layers_to_map(m, layers, lat, lon, buffer_km=buffer_km)

            # show map; returned_objects=[] ensures interaction doesn't re-run
            st_data = st_folium(m, width=700, height=700, returned_objects=[], key="map_display")
        else:
            st.info("No geocoded point available for the query. Try a place name (e.g., 'Kota, Rajasthan').")
