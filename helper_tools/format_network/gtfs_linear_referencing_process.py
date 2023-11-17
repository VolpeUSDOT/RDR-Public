import os
import time
import arcpy
import pandas as pd
from collections import defaultdict

def create_transit_links_gdb(gtfs_folder, output_dir, transit_link_csv, transit_node_csv, logger):
    # INPUTS
    # gtfs_folder = directory containing GTFS text files, specifically shapes.txt
    # output_dir = directory for writing all outputs

    # SETUP
    if not os.path.exists(output_dir):
        logger.info('Making output directory {}'.format(output_dir))
        os.mkdir(output_dir)

    gdb_name = "gtfs_gis.gdb"
    fp_to_gdb = os.path.join(output_dir, gdb_name)

    if arcpy.Exists(fp_to_gdb):
        logger.info('Deleting existing gdb {}'.format(fp_to_gdb))
        arcpy.Delete_management(fp_to_gdb)
        time.sleep(.5)

    logger.info('Creating gdb {}'.format(fp_to_gdb))
    arcpy.CreateFileGDB_management(output_dir, gdb_name)
    arcpy.env.workspace = fp_to_gdb

    # MAIN
    # Converts shapes to GIS format
    logger.info('Creating GIS format of shapes.txt')
    arcpy.conversion.GTFSShapesToFeatures(os.path.join(gtfs_folder, "shapes.txt"), "gtfs_shapes")

    # Converts nodes to GIS format
    logger.info('Creating GIS format of nodes.csv')
    arcpy.management.XYTableToPoint(transit_node_csv, "all_nodes", 'x_coord', 'y_coord', coordinate_system = arcpy.SpatialReference(4326))
    arcpy.MakeFeatureLayer_management("all_nodes", "nodes_lyr")
    # Filter to service nodes only
    arcpy.management.SelectLayerByAttribute("nodes_lyr", "NEW_SELECTION", "node_type LIKE '%service%'")
    arcpy.CopyFeatures_management("nodes_lyr", "service_nodes")

    # Create routes
    logger.info('Linear referencing the shapes')
    arcpy.lr.CreateRoutes("gtfs_shapes", "shape_id", "gtfs_shapes_routes", "LENGTH")

    # Locate stops
    logger.info('Locating stops along the linear referenced shapes')
    arcpy.lr.LocateFeaturesAlongRoutes("service_nodes", "gtfs_shapes_routes", "shape_id", "100 meters", "stops_along_shapes", "shape_id POINT mp", "ALL")

    # Build up the from and to linear events using the above output and the list of stop pairs that we have
    logger.info('Building dictionary of stop mileposts')
    node_mp_dict = defaultdict(dict)
    for row in arcpy.da.SearchCursor("stops_along_shapes", ["shape_id", "node_id", "mp"]):
        shape_id = str(row[0])
        node_id = str(row[1])
        mp = row[2]
        node_mp_dict[shape_id][node_id] = mp

    # Create table to store route events
    logger.info('Creating route event table')
    arcpy.management.CreateTable(fp_to_gdb, "route_event_table")
    arcpy.AddField_management("route_event_table", "link_id", "TEXT")
    arcpy.AddField_management("route_event_table", "shape_id", "TEXT")
    arcpy.AddField_management("route_event_table", "from_node_id", "TEXT")
    arcpy.AddField_management("route_event_table", "from_mp", "DOUBLE")
    arcpy.AddField_management("route_event_table", "to_node_id", "TEXT")
    arcpy.AddField_management("route_event_table", "to_mp", "DOUBLE")

    # Get transit_link_csv into an ArcGIS format
    logger.info('Creating transit link gis table')
    arcpy.management.CreateTable(fp_to_gdb, "transit_link_gis")
    arcpy.AddField_management("transit_link_gis", "from_node_id", "TEXT")
    arcpy.AddField_management("transit_link_gis", "to_node_id", "TEXT")
    arcpy.AddField_management("transit_link_gis", "link_id", "TEXT")
    arcpy.AddField_management("transit_link_gis", "geometry_id", "TEXT")
    arcpy.AddField_management("transit_link_gis", "link_type", "LONG")

    transit_link_gis = pd.read_csv(transit_link_csv, skip_blank_lines=True,
                                   usecols=['link_id', 'link_type', 'from_node_id', 'to_node_id', 'geometry_id'],
                                   converters={'link_id': str, 'link_type': int, 'from_node_id': str, 'to_node_id': str, 'geometry_id': str})
    with arcpy.da.InsertCursor("transit_link_gis", ('from_node_id', 'to_node_id', 'link_id', 'geometry_id', 'link_type')) as icursor:
        for ind, row in transit_link_gis.iterrows():
            icursor.insertRow((row.from_node_id, row.to_node_id, row.link_id, row.geometry_id, row.link_type))

    logger.info('Processing the table of stop-stop pairs')
    # Generate the event layer by iterating through the table of shape/stop pairs and the located stops
    # Note: geometry_id is same as shape_id
    icursor = arcpy.da.InsertCursor("route_event_table", ['link_id', 'shape_id', 'from_node_id', 'from_mp', 'to_node_id', 'to_mp'])
    for row in arcpy.da.SearchCursor("transit_link_gis", ["link_id", "from_node_id", "to_node_id", "geometry_id"], "link_type = 1"):
        link_id = row[0]
        from_node_id = row[1]
        to_node_id = row[2]
        geometry_id = row[3]

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

            icursor.insertRow([link_id, geometry_id, from_node_id, from_mp, to_node_id, to_mp])

    # Make route event layer
    logger.info('Making GIS dataset of route events')
    arcpy.lr.MakeRouteEventLayer("gtfs_shapes_routes", "shape_id", "route_event_table", "shape_id LINE from_mp to_mp", "route_event_lyr")

    # Save to disk
    arcpy.CopyFeatures_management("route_event_lyr", "link_id_routes")
    
    return fp_to_gdb
