import geopandas as gpd
import folium
from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon, Point
import branca

COLOR_MAP = {
    "forest_cover": "green",
    "aquifers": "blue",
    "reservoir": "purple",
    "structure": "orange",
    "inter_basin": "cadetblue"
}

def create_base_map(lat, lon, zoom=7):
    m = folium.Map(location=[lat, lon], zoom_start=zoom, control_scale=True)
    folium.Marker([lat, lon], popup="Query Location", icon=folium.Icon(color="red", icon="info-sign")).add_to(m)
    return m

def _add_legend(m, color_map):
    # Small HTML/CSS legend inserted as a FloatImage-like element (branca)
    items = ""
    for k, c in color_map.items():
        label = {
            "forest_cover": "Forest Cover",
            "aquifers": "Aquifers",
            "reservoir": "Reservoirs",
            "structure": "Structures",
            "inter_basin": "Inter-Basin Links"
        }.get(k, k)
        items += f"""
            <div style="display:flex;align-items:center;margin-bottom:6px">
              <div style="width:16px;height:16px;border-radius:2px;background:{c};margin-right:8px;border:1px solid #222"></div>
              <div style="font-size:14px">{label}</div>
            </div>
        """

    html = f"""
    <div style="
        background: white;
        border-radius:8px;
        padding:12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25);
        font-family: Roboto, Arial, sans-serif;
        ">
      <strong style="font-size:15px;display:block;margin-bottom:8px">Legend</strong>
      {items}
    </div>
    """

    legend = branca.element.MacroElement()
    legend._template = branca.element.Template(f"""
    {{% macro html(this, kwargs) %}}
      <div style="position: absolute; bottom: 12px; right: 12px; z-index: 9999;">
        {html}
      </div>
    {{% endmacro %}}
    """)
    m.get_root().add_child(legend)

def add_layers_to_map(m, layers, lat, lon, buffer_km=100):
    point = Point(lon, lat)
    point_proj = gpd.GeoSeries([point], crs="EPSG:4326").to_crs(3857).iloc[0]

    for layer_name, gdf in layers.items():
        try:
            gdf_proj = gdf.to_crs(3857)
            nearby = gdf_proj[gdf_proj.geometry.distance(point_proj) <= buffer_km * 1000]

            if nearby.empty:
                continue

            nearby = nearby.to_crs(4326)
            color = COLOR_MAP.get(layer_name, "gray")

            for _, row in nearby.iterrows():
                geom = row.geometry

                if isinstance(geom, (Polygon, MultiPolygon)):
                    folium.GeoJson(
                        geom,
                        style_function=lambda feat, col=color: {
                            "color": col,
                            "weight": 2.2,
                            "fillOpacity": 0.35
                        }
                    ).add_to(m)

                elif isinstance(geom, Point):
                    folium.CircleMarker(
                        location=[geom.y, geom.x],
                        radius=6,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity = 0.9
                    ).add_to(m)

                elif isinstance(geom, (LineString, MultiLineString)):
                    folium.GeoJson(
                        geom,
                        style_function=lambda feat, col=color: {
                            "color": col,
                            "weight": 3.0
                        }
                    ).add_to(m)

        except Exception as e:
            print(f"Error adding layer {layer_name}: {e}")

    _add_legend(m, COLOR_MAP)
    return m
