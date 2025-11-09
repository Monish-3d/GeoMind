import geopandas as gpd

#path = "data/spatial/forest_cover/State_ForestFSI.shp"

paths = ["data/spatial/forest_cover/State_ForestFSI.shp" ,
         "data/spatial/aquifers/Aquif_Mat.shp",
         "data/spatial/inter_basin/Structure.shp" ,
         "data/spatial/inter_basin/Inter_Basin_Transfer_Link.shp",
         "data/spatial/reservoir/Reservoir.shp"]

for path in paths:
    gdf = gpd.read_file(path)

    print("Columns:", list(gdf.columns))
    print("\n Sample rows:")
    print(gdf.head(2))
