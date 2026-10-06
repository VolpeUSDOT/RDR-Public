import os
import time
import sys
import pandas as pd
from collections import defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "common"))

# Make sure the gdal dll are available
if "CONDA_PREFIX" in os.environ:
    conda_path = os.environ["CONDA_PREFIX"]

    if sys.platform == "win32":
        gdal_path = os.path.join(conda_path, "Library", "share", "gdal")
        proj_path = os.path.join(conda_path, "Library", "share", "proj")
    else:
        gdal_path = os.path.join(conda_path, "share", "gdal")
        proj_path = os.path.join(conda_path, "share", "proj")

    # Inject paths into the environment if they exist
    if os.path.exists(gdal_path):
        os.environ["GDAL_DATA"] = gdal_path
    if os.path.exists(proj_path):
        os.environ["PROJ_DATA"] = proj_path
        os.environ["PROJ_LIB"] = proj_path  # Fallback for older pyproj versions

import geopandas as gpd
import shared_tools
import shapely
from shapely.ops import substring


# ==================================================================


def GTFSShapesToFeatures(gtfs_folder, fp_to_gpkg):
    """Converts gtfs data to a geopackage feature class
    Args:
        gtfs_folder: path to the gtfs files folder
        fp_to_gpkg: path to the output geopackage
    Returns:
        geodataframe with the shape_id field and the geometry field
    """
    from pathlib import Path
    gtfs_path = Path(gtfs_folder)
    shapes_path = gtfs_path / "shapes.txt"
    routes_path = gtfs_path / "routes.txt"
    trips_path = gtfs_path / "trips.txt"
    # absolutely need the shapes.txt file
    if shapes_path.exists() is False:
        raise Exception("GTFS shapes.txt is not found.")
    # read in as a dataframe
    df = pd.read_csv(shapes_path, converters={'shape_id': str})
    # preps the lat long so it can be converted to a WKT string
    df["LAT_LONG"] = df[["shape_pt_lat", "shape_pt_lon"]].apply(lambda x: f"{x['shape_pt_lon']} {x['shape_pt_lat']}", axis=1)
    # group the coordinate pairs by the shape_id sorted by their sequence
    agg_df = df.sort_values(["shape_id", "shape_pt_sequence"]).groupby("shape_id")["LAT_LONG"].agg(list).reset_index()
    # create the WKT string
    agg_df["LAT_LONG_ASSTR"] = agg_df["LAT_LONG"].apply(lambda x: ",".join(x))
    agg_df["WKT_LINESTR"] = agg_df["LAT_LONG_ASSTR"].apply(lambda x: f"LINESTRING ({x})")

    # if the routes and trips exist then we can add in the other pieces of information. Route has shape_id and that links to trips
    if routes_path.exists() and trips_path.exists():
        routes_df = pd.read_csv(routes_path, converters={'route_id':str, 'route_type':str})
        trips_df = pd.read_csv(trips_path, converters={'route_id':str, 'trip_id':str, 'shape_id':str}, usecols=['route_id', 'shape_id'])
        group = trips_df.groupby(['route_id', 'shape_id']).count().reset_index()
        agg_df = agg_df.merge(group, left_on="shape_id", right_on="shape_id", how='left')
        agg_df = agg_df.merge(routes_df, left_on="route_id", right_on="route_id", how='left')

    # convert to geodataframe and save to the geopackage
    geometry = gpd.GeoSeries.from_wkt(agg_df["WKT_LINESTR"])
    gdf = gpd.GeoDataFrame(agg_df, geometry=geometry, crs="EPSG:4326")
    gdf.to_file(
        fp_to_gpkg,
        layer="gtfs_shapes",
        driver="GPKG",
        index=True
    )

    return gdf[["shape_id", "geometry"]]


# ==================================================================


def create_transit_links_gdb(gtfs_folder, output_dir, transit_link_csv, transit_node_csv, logger):
    # INPUTS
    # gtfs_folder = directory containing GTFS text files, specifically shapes.txt
    # output_dir = directory for writing all outputs

    # SETUP
    if not os.path.exists(output_dir):
        logger.info('Making output directory {}'.format(output_dir))
        os.mkdir(output_dir)

    gpkg_name = "gtfs_gis.gpkg"
    fp_to_gpkg = os.path.join(output_dir, gpkg_name)

    # MAIN
    # Converts shapes to GIS format
    logger.info('Creating GIS format of shapes.txt')
    gdf_gtfs = GTFSShapesToFeatures(gtfs_folder, fp_to_gpkg)

    # Converts nodes to GIS format
    logger.info('Creating GIS format of nodes.csv')

    # convert the nodes to a geopackage
    transit_node_df = pd.read_csv(transit_node_csv, converters={'node_id': str})
    all_nodes = gpd.GeoDataFrame(
        transit_node_df,
        geometry=gpd.points_from_xy(
            transit_node_df["x_coord"], transit_node_df["y_coord"]
        ),
        crs="EPSG:4326",
    )

    # Filter to service nodes only
    nodes_lyr = all_nodes[all_nodes['node_type'].str.contains('service', case=False, na=False)]
    nodes_lyr.to_file(fp_to_gpkg, layer="service_nodes", driver="GPKG")
    all_nodes.to_file(fp_to_gpkg, layer="all_nodes", driver="GPKG")

    # temporarily project to utm so they can be buffered
    utm_crs = nodes_lyr.estimate_utm_crs()
    nodes_projected = nodes_lyr.to_crs(utm_crs)
    routes_projected = gdf_gtfs.to_crs(utm_crs)

    nodes_buffered = nodes_projected.copy()
    nodes_buffered["buffer_geom"] = nodes_projected.geometry.buffer(100)
    nodes_buffered = nodes_buffered.set_geometry("buffer_geom")

    # join the buffered nodes to the route data
    selected_nodes = gpd.sjoin(
        nodes_buffered,
        routes_projected[["shape_id",routes_projected.geometry.name]],  # Only pull attributes; sjoin drops right geometries
        how="inner",
        predicate="intersects",
    )

    node_mp_dict = defaultdict(dict)
    stops_along_shapes_ph = []

    # this no longer converts to a route layer since there isn't an equivalent in geopandas
    # gets the projected point along the line, assumes the measure is the same as the length
    
    for _, row in selected_nodes.iterrows():
        node_id = str(row["node_id"])
        shape_id = str(row["shape_id"])

        if not pd.isnull(node_id) and not pd.isnull(shape_id):
            additional_values = nodes_lyr[nodes_lyr["node_id"]==node_id][["x_coord", "y_coord", "node_type", "orig_node_id"]].iloc[0].tolist()
            node_geom = nodes_lyr[nodes_lyr["node_id"]==node_id][nodes_lyr.geometry.name].values[0]
            line_geom = gdf_gtfs[gdf_gtfs["shape_id"]==shape_id][gdf_gtfs.geometry.name].values[0]
            results = line_geom.project(node_geom)
            node_mp_dict[shape_id][node_id] = results
            stops_along_shapes_ph.append([shape_id, results, node_id] + additional_values)

    stops_along_shapes_df = pd.DataFrame(stops_along_shapes_ph, columns=["shape_id", "mp", "node_id", "x_coord", "y_coord", "node_type", "orig_node_id"])
    gpd.GeoDataFrame(stops_along_shapes_df).to_file(
        fp_to_gpkg, layer="stops_along_shapes", driver="GPKG"
    )

    transit_link_gis = pd.read_csv(transit_link_csv, skip_blank_lines=True,
                                   usecols=['link_id', 'link_type', 'from_node_id', 'to_node_id', 'geometry_id'],
                                   converters={'link_id': str, 'link_type': int, 'from_node_id': str, 'to_node_id': str, 'geometry_id': str})
    transit_link_gis_table = gpd.GeoDataFrame(transit_link_gis)
    transit_link_gis_table.to_file(
        fp_to_gpkg, layer="transit_link_gis", driver="GPKG"
    )

    # Create table to store route events
    logger.info('Creating route event table')

    placeholder_table = []
    link_id_routes_ph = []
    logger.info('Processing the table of stop-stop pairs')
    
    for _, row in transit_link_gis_table[transit_link_gis_table["link_type"]==1].iterrows():
        link_id = row["link_id"]
        from_node_id = row["from_node_id"]
        to_node_id = row["to_node_id"]
        geometry_id = row["geometry_id"]

        # Check for key errors and tell user to check routes.txt for unsupported route types
        if geometry_id not in node_mp_dict:
            logger.warning(
                'The geometry_id (shape_id) {} was not found. Check {} and ensure that nodes listed there are present in {}.'.format(geometry_id, transit_node_csv, transit_link_csv)
                )
        
        elif from_node_id not in node_mp_dict[geometry_id]:
            logger.warning(
                'The node_id {} was not found. Only tram, subway, rail, and bus are currently supported by this helper tool.'.format(from_node_id)
                )
        
        elif to_node_id not in node_mp_dict[geometry_id]:
            logger.warning(
                'The node_id {} was not found. Only tram, subway, rail, and bus are currently supported by this helper tool.'.format(to_node_id)
                )

        else:
            from_mp = node_mp_dict[str(geometry_id)][from_node_id]
            to_mp = node_mp_dict[str(geometry_id)][to_node_id]

            placeholder_table.append([link_id, geometry_id, from_node_id, from_mp, to_node_id, to_mp])
            orig_shape = gdf_gtfs[gdf_gtfs["shape_id"]==geometry_id][gdf_gtfs.geometry.name].values[0]
            link_id_routes_ph.append([link_id, geometry_id, from_node_id, from_mp, to_node_id, to_mp, substring(orig_shape, from_mp, to_mp)])

    route_event_table = pd.DataFrame(placeholder_table, columns=["link_id", "shape_id",
                         "from_node_id", "from_mp",
                         "to_node_id", "to_mp"])
    gpd.GeoDataFrame(route_event_table).to_file(
        fp_to_gpkg, layer="route_event_table", driver="GPKG"
    )
    link_id_routes_ph = pd.DataFrame(link_id_routes_ph, columns=["link_id", "shape_id",
                         "from_node_id", "from_mp",
                         "to_node_id", "to_mp", "geometry"])
    gpd.GeoDataFrame(link_id_routes_ph, geometry="geometry", crs="EPSG:4326").to_file(
        fp_to_gpkg, layer="link_id_routes", driver="GPKG"
    )

    return fp_to_gpkg
