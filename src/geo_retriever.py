import os
import geopandas as gpd
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import streamlit as st

SPATIAL_ROOT = "data/spatial"

# Explicit mentioned shapefiles (will probably changed later??)
SHAPEFILES = {
    "aquifers":     "aquifers/Aquif_Mat.shp",
    "forest_cover": "forest_cover/State_ForestFSI.shp",
    "reservoir":    "reservoir/Reservoir.shp",
    "structure":    "inter_basin/Structure.shp",
    "inter_basin":  "inter_basin/Inter_Basin_Transfer_Link.shp",
}

@st.cache_resource(show_spinner=False)
def load_all_layers():
    layers = {}
    for key, rel_path in SHAPEFILES.items():
        full_path = os.path.join(SPATIAL_ROOT, rel_path)
        if not os.path.exists(full_path):
            print(f"Warning: shapefile not found: {full_path}")
            layers[key] = gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
            continue

        gdf = gpd.read_file(full_path)
        if gdf.crs is None:
            gdf = gdf.set_crs(4326)
        else:
            gdf = gdf.to_crs(4326)
        layers[key] = gdf
        print(f"Loaded {key} ({len(gdf)} records)")
    return layers

# Geocoder
geolocator = Nominatim(user_agent="GeoRAG")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def _f(x):
    """Safe float -> 2dp (for numeric shapefile attrs that may be None/str)."""
    try:
        return round(float(x or 0), 2)
    except Exception:
        return 0.0

def get_spatial_context(location_query: str, all_layers=None):
    """
    Geocode a place and summarize the nearest/intersecting features from each layer,
    including layer-specific attributes and an accurate distance_km.
    """
    if all_layers is None:
        all_layers = load_all_layers()

    loc = geocode(location_query)
    if loc is None:
        return {"error": f"Location '{location_query}' not found"}

    lon, lat = loc.longitude, loc.latitude
    point_wgs84 = Point(lon, lat)

    summary = {
        "location": loc.address,
        "latitude": lat,
        "longitude": lon,
        "layers": {},
    }

    # Use metric CRS for distance calculation
    point_3857 = gpd.GeoSeries([point_wgs84], crs="EPSG:4326").to_crs(3857).iloc[0]

    # ~0.35° buffer ≈ ~40 km in WGS84 for a quick intersect
    search_buffer_deg = 0.35

    for layer_name, gdf in all_layers.items():

        if gdf.empty or gdf.geometry.isnull().all():
            continue
        # Intersect first; if none, fall back to nearest
        matches = gdf[gdf.geometry.intersects(point_wgs84.buffer(search_buffer_deg))]
        gdf_3857 = gdf.to_crs(3857)

        if not matches.empty:
            candidates = matches.to_crs(3857).copy()
        else:
            candidates = gdf_3857.copy()

        candidates["distance_km"] = candidates.geometry.distance(point_3857) / 1000.0
        best = candidates.sort_values("distance_km").iloc[0]
        distance_km = round(float(best["distance_km"]), 2)

        # Align to original row (WGS84) if possible
        attributes = gdf.loc[best.name].to_dict() if best.name in gdf.index else best.to_dict()

        # Layer-specific summaries
        if layer_name == "forest_cover":
            summary["layers"][layer_name] = {
                "state": attributes.get("State_Name"),
                "total_forest_area_sqkm": _f(attributes.get("Forest_201")),
                "percent_forest_cover": _f(attributes.get("Per_GA_201")),
                "change_since_2017_sqkm": _f(attributes.get("Ch_wrt2017")),
                "change_percent": _f(attributes.get("Ch_per")),
                "distance_km": distance_km,
            }

        elif layer_name == "aquifers":
            summary["layers"][layer_name] = {
                "state_code": attributes.get("Name_of_St"),
                "aquifer_type": attributes.get("Type_of_Aq"),
                "distance_km": distance_km,
            }

        elif layer_name == "structure":
            summary["layers"][layer_name] = {
                "structure_name": attributes.get("STRUCTURE_"),
                "structure_type": attributes.get("STRUC_TYPE"),
                "status": attributes.get("STRUC_STAT"),
                "distance_km": distance_km,
            }

        elif layer_name == "inter_basin":
            summary["layers"][layer_name] = {
                "link_name": attributes.get("LINK_NAME"),
                "component": attributes.get("COMPONENT"),
                "type": attributes.get("TYPE"),
                "distance_km": distance_km,
            }

        elif layer_name == "reservoir":
            summary["layers"][layer_name] = {
                "name": attributes.get("wbname"),
                "state": attributes.get("state"),
                "area_ha": attributes.get("area_ha"),
                "distance_km": distance_km,
            }

        else:
            clean = {k: ("" if v is None else str(v)) for k, v in attributes.items()}
            clean["distance_km"] = distance_km
            summary["layers"][layer_name] = clean

    return summary

def summarize_spatial_context(spatial_data):
    """
    Turn the structured dict into readable Markdown.
    (No leading spaces; always returns a non-empty string.)
    """
    if not isinstance(spatial_data, dict):
        return "_No spatial data available._"

    if "error" in spatial_data:
        return f"**Spatial lookup failed:** {spatial_data['error']}"

    loc = spatial_data["location"]
    L = spatial_data["layers"]

    lines = [f"### Spatial Context Summary for **{loc}**", ""]

    # FOREST
    f = L.get("forest_cover")
    if isinstance(f, dict):
        lines.append(
            f"- **Forest Cover:** {f['state']} — "
            f"{f['total_forest_area_sqkm']} sq km "
            f"({f['percent_forest_cover']}%). "
            f"Δ since 2017: {f['change_since_2017_sqkm']} sq km "
            f"({f['change_percent']}%). "
            f"(~{f['distance_km']} km)"
        )

    # AQUIFERS
    a = L.get("aquifers")
    if isinstance(a, dict):
        lines.append(
            f"- **Aquifer:** Type {a.get('aquifer_type','?')} in state {a.get('state_code','?')} "
            f"(~{a.get('distance_km',0)} km)"
        )

    # RESERVOIRS
    r = L.get("reservoir")
    if isinstance(r, dict):
        lines.append(
            f"- **Reservoir:** {r['name']} in {r['state']}, "
            f"area {r['area_ha']} ha "
            f"(~{r['distance_km']} km)"
        )

    # STRUCTURES
    s = L.get("structure")
    if isinstance(s, dict):
        lines.append(
            f"- **Structure:** {s.get('structure_name','Unknown')} "
            f"({s.get('structure_type','?')}, {s.get('status','?')}) "
            f"(~{s.get('distance_km',0)} km)"
        )

    # INTER-BASIN
    i = L.get("inter_basin")
    if isinstance(i, dict):
        lines.append(
            f"- **Inter-Basin Link:** {i.get('link_name','Unnamed')} "
            f"({i.get('component','?')}, Type {i.get('type','?')}) "
            f"(~{i.get('distance_km',0)} km)"
        )
    # will add major acquifers later....
    # If none added,
    if len(lines) <= 2:
        lines.append("No nearby spatial features found.")

    return "\n".join(lines)
