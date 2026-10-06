import os
import pandas as pd
import numpy as np
import datetime
import argparse
import sys
from math import radians, cos, sin, asin, sqrt
import network_config_reader
import gtfs_linear_referencing_process

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "metamodel_py"))
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
import shapely
import shared_tools
import rdr_setup
import rdr_supporting

VERSION_NUMBER = "2026.1"
VERSION_DATE = "9/30/2026"

# ---------------------------------------------------------------------------------------------------
# The following code creates transit centroid connectors by building buffer zones around transit
# boarding nodes and identifying TAZs within the buffer and (optionally) builds a geodatabase of
# transit network links from GTFS and GMNS network data
# ---------------------------------------------------------------------------------------------------


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in miles between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 3959.87433  # this is in miles
    return c * r

    
def transit_overlay(cfg, logger):

    # Values from config file
    output_dir = cfg['output_dir']
    run_name = cfg['run_id']

    # Path to roadway network node CSV file
    # Node CSV file should contain all transportation network centroids and road intersections
    # Node type field should be clearly specified as one of the following: centroid, road intersection
    road_node_csv = cfg['road_node_csv']
    if not os.path.exists(road_node_csv):
        logger.error('The roadway network node CSV file ' + road_node_csv + ' does not exist')
        raise Exception("NODE CSV FILE ERROR: input road_node_csv {} can't be found".format(road_node_csv))
    centroid_nodes = pd.read_csv(road_node_csv, usecols=['node_id', 'x_coord', 'y_coord', 'node_type'],
                                 converters={'node_id': str, 'x_coord': str, 'y_coord': str, 'node_type': str})
    centroid_nodes = centroid_nodes[centroid_nodes['node_type'] == 'centroid']

    # Path to transit network node CSV file
    # Node CSV file should contain all transit stops and service nodes (can be created by GTFS2GMNS tool)
    # Node type field should be clearly specified as one of the following: stop (for bus), rail_station, metro_station, tram_service_node, metro_service_node, rail_service_node, bus_service_node
    transit_node_csv = os.path.join(output_dir, 'transit_node_temp.csv')
    if not os.path.exists(transit_node_csv):
        logger.error('The transit network node CSV file ' + transit_node_csv + ' does not exist')
        raise Exception("NODE CSV FILE ERROR: input transit_node_csv {} can't be found".format(transit_node_csv))
    boarding_nodes = pd.read_csv(transit_node_csv, usecols=['node_id', 'x_coord', 'y_coord', 'node_type'],
                                 converters={'node_id': str, 'x_coord': str, 'y_coord': str, 'node_type': str})
    boarding_nodes = boarding_nodes[~boarding_nodes['node_type'].str.endswith("service_node")]

    # Check the node_id fields do not overlap
    if len(set(centroid_nodes['node_id']) & set(boarding_nodes['node_id'])) > 0:
        logger.warning('The roadway and transit network node CSV files have overlapping node IDs. Transit network nodes will be renumbered.')

    # Path to TAZ shapefile
    # This is used to identify which TAZs can access which transit nodes
    if not os.path.exists(cfg['TAZ_shapefile']):
        logger.error('The TAZ shapefile ' + cfg['TAZ_shapefile'] + ' does not exist')
        raise Exception("TAZ FILE ERROR: input TAZ_shapefile {} can't be found".format(cfg['TAZ_shapefile']))
    
    # get the taz data path
    TAZ_shapefile = shared_tools.get_vector_inputs(cfg['TAZ_shapefile'])

    # Search distance
    # Search radius for determining the maximum threshold of travel from a TAZ to a transit node
    # Includes units (e.g., feet, meters, yards)
    search_distance = cfg['search_distance']
    
    gdb = 'RDR_Transit_Overlay'
    full_path_gpkg = os.path.join(output_dir, gdb + '.gpkg')
    # create a geodataframe from the nodes
    transit_fc = gpd.GeoDataFrame(
        boarding_nodes,
        geometry=gpd.points_from_xy(
            boarding_nodes["x_coord"], boarding_nodes["y_coord"]
        ),
        crs="EPSG:4326",
    )
    # write to a geopacakage
    transit_fc.to_file(full_path_gpkg, layer="transit_layer")
    transit_fc_orig = transit_fc.copy()

    # project to utm if it is a geographic CRS
    if transit_fc_orig.crs.is_geographic is True:
        logger.info(
            "Projecting to UTM for analysis."
        )
        utm_crs = transit_fc_orig.estimate_utm_crs()
        transit_fc = transit_fc_orig.to_crs(utm_crs)

    # Create buffers for transit nodes
    # Get the search value and distance unit. Get the conversion to utm factor as needed
    search_distance_value, search_distance_unit = shared_tools.separate_distance_unit(search_distance)
    search_distance_unit_to_gdf_units = (shared_tools.standardize_units(search_distance_unit), shared_tools.standardize_units(transit_fc.crs.axis_info[0].unit_name))
    factor = 1 if len(set(search_distance_unit_to_gdf_units)) <= 1 else shared_tools.DISTANCE_CONVERSIONS[search_distance_unit_to_gdf_units]
    max_distance = search_distance_value * factor

    # buffer the transit layer
    transit_buffer = transit_fc.copy()
    transit_buffer_geom = transit_fc.buffer(max_distance)
    transit_buffer["geometry"] = transit_buffer_geom
    transit_buffer.to_file(full_path_gpkg, layer="transit_layer_buffer")
    
    # Create feature layer for TAZ polygons
    if len(TAZ_shapefile) == 2:
        TAZ_layer = gpd.read_file(TAZ_shapefile[0], layer=TAZ_shapefile[1])
    elif len(TAZ_shapefile) == 1:
        TAZ_layer = gpd.read_file(TAZ_shapefile[0])
    else:
        logger.info("Unsupported vector format for TAZ polygon input.")
        raise Exception("Unsupported vector format for TAZ polygon input.")

    # project to the same crs as the transit data
    TAZ_layer.to_crs(transit_fc.crs, inplace=True)

    # intersect with the transit buffers
    TAZ_transit_intersect = gpd.overlay(TAZ_layer, transit_buffer[["node_id","geometry"]], how="intersection")
    TAZ_transit_intersect.to_file(full_path_gpkg, layer="TAZ_transit_intersect")
    # look up TAZ ID field
    zone_ID = cfg['zone_ID']
    
    # Create dataframe of centroid -> transit boarding node connectors
    df = pd.DataFrame(TAZ_transit_intersect.drop(columns=TAZ_transit_intersect.geometry.name)).replace(-99999, 0).reset_index()
    df = df.astype({zone_ID : 'str', 'node_id' : 'str'})
    df = pd.merge(df, centroid_nodes, how='left', left_on=zone_ID, right_on='node_id', suffixes=('', '_y'))
    df.rename({'node_id_y': 'centroid_node_id', 'x_coord': 'from_x', 'y_coord': 'from_y'}, axis='columns', inplace=True)
    df = pd.merge(df, boarding_nodes, how='left', on='node_id')
    df.rename({'node_id': 'transit_node_id', 'x_coord': 'to_x', 'y_coord': 'to_y'}, axis='columns', inplace=True)
    # Create dataframe of transit boarding -> centroid node connectors
    df_copy = df.copy(deep=True)
    df.rename({'centroid_node_id': 'from_node_id', 'transit_node_id': 'to_node_id'}, axis='columns', inplace=True)
    df_copy.rename({'centroid_node_id': 'to_node_id', 'transit_node_id': 'from_node_id',
                    'from_x': 'to_x', 'from_y': 'to_y', 'to_x': 'from_x', 'to_y': 'from_y'}, axis='columns', inplace=True)
    transit_cc = pd.concat([df, df_copy], ignore_index=True)
    transit_cc = transit_cc[['from_node_id', 'to_node_id', 'from_x', 'from_y', 'to_x', 'to_y']]

    # Create other link CSV fields
    transit_cc['directed'] = 1
    # Calculate length from xy coordinates and Haversine formula
    transit_cc['length'] = transit_cc.apply(lambda row : haversine(float(row['from_x']), float(row['from_y']), float(row['to_x']), float(row['to_y'])),
                                            axis=1)
    transit_cc['facility_type'] = 903
    transit_cc['capacity'] = 10000
    transit_cc['free_speed'] = 3
    transit_cc['lanes'] = 1
    transit_cc['allowed_uses'] = 'c'
    transit_cc['WKT'] = 'LINESTRING(' + transit_cc['from_x'].astype(str) + ' ' + transit_cc['from_y'].astype(str) + ', ' + transit_cc['to_x'].astype(str) + ' ' + transit_cc['to_y'].astype(str) + ')'
    transit_cc['link_id'] = np.arange(len(transit_cc)) + 1

    logger.info('Writing transit centroid connector file as {} to directory {}'.format('transit_cc_link.csv', output_dir))
    transit_cc.to_csv(os.path.join(output_dir, 'transit_cc_link.csv'), index=False,
                      columns=['link_id', 'from_node_id', 'to_node_id', 'from_x', 'from_y', 'to_x', 'to_y',
                               'directed', 'length', 'facility_type', 'capacity', 'free_speed', 'lanes',
                               'allowed_uses', 'WKT'])


def main():

    start_time = datetime.datetime.now()

    # PARSE ARGS
    # ----------------------------------------------------------------------------------------------

    program_description = 'Resilience Disaster Recovery Prepare RDR Transit Network Helper Tool: ' \
                          + VERSION_NUMBER + ", (" + VERSION_DATE + ")"

    help_text = """
    The command-line input expected for this script is as follows:

    TheFilePathOfThisScript ConfigFilePath
    """

    parser = argparse.ArgumentParser(description=program_description, usage=help_text)


    if len(sys.argv) not in (2, 3):
        parser.print_help()
        sys.exit()

    parser.add_argument("config_file", help="The full path to the XML Scenario", type=str)
    parser.add_argument("root_dir", help="The root dir", type=str, nargs="?", default=None)
    
    args = parser.parse_args()

    # ---------------------------------------------------------------------------------------------------
    # SETUP
    if not os.path.exists(args.config_file):
        print("ERROR: config file {} can't be found!".format(args.config_file))
        sys.exit()

    cfg = network_config_reader.read_network_config_file(args.config_file, args.root_dir)

    # Output of this helper tool along w/ log files are put in the output dir
    run_name = cfg['run_id']
    output_dir = cfg['output_dir']

    # Set up logging
    logger = rdr_supporting.create_loggers(output_dir, 'prep_network', cfg)

    logger.info("=========================================================================")
    logger.info("============== PREPARE RDR TRANSIT NETWORK STARTING =====================")
    logger.info("=========================================================================")

    logger.info("Starting prepare RDR transit network helper tool run...")

    # Combine all files into combined node and link output files
    # Node CSV node_type field should be clearly specified as one of the following: centroid, road intersection, transit boarding, transit
    # Link CSV required fields are link_id, from_node_id, to_node_id, directed, length (miles), facility_type, capacity, free_speed (mph), lanes, allowed_uses

    # Path to roadway network node CSV file
    # Node CSV file should contain all transportation network centroids and road intersections
    # Required fields are node_id, x_coord, y_coord, node_type
    # Node type field should be clearly specified as one of the following: 'centroid', 'road intersection'
    road_node_csv = cfg['road_node_csv']
    road_nodes = pd.read_csv(road_node_csv, skip_blank_lines=True,
                             usecols=['node_id', 'x_coord', 'y_coord', 'node_type'],
                             converters={'node_id': str, 'x_coord': str, 'y_coord': str, 'node_type': str})

    # Path to transit network node CSV file
    # Node CSV file should contain all transit stops and service nodes (can be created by GTFS2GMNS tool)
    # Required fields are node_id, x_coord, y_coord, node_type
    # Node type field should be clearly specified as one of the following: stop (for bus), rail_station, metro_station, tram_service_node, metro_service_node, rail_service_node, bus_service_node
    # Node type field will be converted to 'transit boarding' or 'transit'
    transit_node_csv = cfg['transit_node_csv']
    transit_nodes = pd.read_csv(transit_node_csv, skip_blank_lines=True,
                                usecols=['node_id', 'x_coord', 'y_coord', 'node_type'],
                                converters={'node_id': str, 'x_coord': str, 'y_coord': str, 'node_type': str})
    
    # Check the node_id fields do not overlap
    if len(set(road_nodes['node_id']) & set(transit_nodes['node_id'])) > 0:
        logger.warning('The roadway and transit network node CSV files have overlapping node IDs. Transit network nodes will be renumbered.')

    # Path to roadway network link CSV file
    # Link CSV file should contain all road centroid connectors and road links
    # Required fields are link_id, from_node_id, to_node_id, directed, length (miles), facility_type, capacity, free_speed (mph), lanes, allowed_uses
    # Centroid connectors should have facility_type = 901, high capacity, low free_speed, lanes = 1
    road_link_csv = cfg['road_link_csv']
    road_links = pd.read_csv(road_link_csv, skip_blank_lines=True,
                             usecols=['link_id', 'from_node_id', 'to_node_id', 'directed', 'length', 'facility_type',
                                      'capacity', 'free_speed', 'lanes'],
                             converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, 'directed': int,
                                         'length': float, 'facility_type': str, 'capacity': float, 'free_speed': float,
                                         'lanes': int})

    # Check the default transit facility types are not used by road link CSV file (reserved for transit)
    if sum(road_links['facility_type'].isin(['100', '101', '102', '103', '600', '601', '602', '603', '700', '701', '702', '703', '801', '903'])) > 0:
        logger.error('Roadway link facility_type field should not use values reserved for transit links (e.g., 100-103, 600-603, 700-703, 801, 903). Please update the road_link_csv file and run again.')
        raise Exception("LINK CSV FILE ERROR: roadway link facility types should not be set to reserved transit facility types (see log file for specific values)")

    # Path to transit network link CSV file
    # Link CSV file should contain all transit service, boarding/deboarding, and transfer links (can be created by GTFS2GMNS tool)
    # Required input fields are link_id, from_node_id, to_node_id, facility_type, link_type, dir_flag, length (miles), lanes, capacity, free_speed (miles per hour)
    # Facility type field should be clearly specified as one of the following: tram, metro, rail, bus, sta2sta (for transfer links)
    # Link type field should be clearly specified as one of the following: 1 (for service links), 2 (for boarding/deboarding links), 3 (for transfer links)
    # Lanes will be reset to 1
    # Facility type field will be converted to corresponding default transit facility types
    transit_link_csv = cfg['transit_link_csv']
    create_gpkg = cfg['create_gpkg']
    if create_gpkg:
        transit_links = pd.read_csv(transit_link_csv, skip_blank_lines=True,
                                    usecols=['link_id', 'from_node_id', 'to_node_id', 'dir_flag', 'length', 'facility_type',
                                             'link_type', 'capacity', 'free_speed', 'lanes', 'geometry_id'],
                                    converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, 'dir_flag': int,
                                                'length': float, 'facility_type': str, 'link_type': int, 'capacity': float,
                                                'free_speed': float, 'lanes': int, 'geometry_id': str})
    else:
        transit_links = pd.read_csv(transit_link_csv, skip_blank_lines=True,
                                    usecols=['link_id', 'from_node_id', 'to_node_id', 'dir_flag', 'length', 'facility_type',
                                             'link_type', 'capacity', 'free_speed', 'lanes'],
                                    converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, 'dir_flag': int,
                                                'length': float, 'facility_type': str, 'link_type': int, 'capacity': float,
                                                'free_speed': float, 'lanes': int})
        transit_links['geometry_id'] = ''
        transit_links['geometry_id'] = transit_links['geometry_id'].astype('str')
    transit_links.rename({'dir_flag': 'directed'}, axis='columns', inplace=True)
    transit_links['lanes'] = 1
    # Transfer links
    transit_links['facility_type'] = np.where(transit_links['facility_type'] == 'sta2sta',
                                              '801', transit_links['facility_type'])
    # Service links
    transit_links['facility_type'] = np.where((transit_links['facility_type'] == 'tram') & (transit_links['link_type'] == 1),
                                              '100', transit_links['facility_type'])
    transit_links['facility_type'] = np.where((transit_links['facility_type'] == 'metro') & (transit_links['link_type'] == 1),
                                              '101', transit_links['facility_type'])
    transit_links['facility_type'] = np.where((transit_links['facility_type'] == 'rail') & (transit_links['link_type'] == 1),
                                              '102', transit_links['facility_type'])
    transit_links['facility_type'] = np.where((transit_links['facility_type'] == 'bus') & (transit_links['link_type'] == 1),
                                              '103', transit_links['facility_type'])
    # Boarding and deboarding links
    transit_links['facility_type'] = np.where((transit_links['facility_type'] == 'tram') & (transit_links['link_type'] == 2),
                                              np.where(transit_links['from_node_id'] <= transit_links['to_node_id'],
                                                       '600', '700'),
                                              transit_links['facility_type'])
    transit_links['facility_type'] = np.where((transit_links['facility_type'] == 'metro') & (transit_links['link_type'] == 2),
                                              np.where(transit_links['from_node_id'] <= transit_links['to_node_id'],
                                                       '601', '701'),
                                              transit_links['facility_type'])
    transit_links['facility_type'] = np.where((transit_links['facility_type'] == 'rail') & (transit_links['link_type'] == 2),
                                              np.where(transit_links['from_node_id'] <= transit_links['to_node_id'],
                                                       '602', '702'),
                                              transit_links['facility_type'])
    transit_links['facility_type'] = np.where((transit_links['facility_type'] == 'bus') & (transit_links['link_type'] == 2),
                                              np.where(transit_links['from_node_id'] <= transit_links['to_node_id'],
                                                       '603', '703'),
                                              transit_links['facility_type'])

    # Warn user about blank values in facility type
    if sum(transit_links['facility_type'] == '') > 0:
        logger.warning('{} entries in facility_type field of transit link CSV are blank.'.format(sum(transit_links['facility_type'] == '')))

    # Save original transit node ID
    transit_nodes['orig_node_id'] = transit_nodes['node_id']

    # Find duplicate node IDs between transit and road networks and renumber starting with max existing node ID
    transit_nodes.loc[transit_nodes['node_id'].isin(road_nodes['node_id']), ['node_id']] = np.arange(sum(transit_nodes['node_id'].isin(road_nodes['node_id'].astype(int)))) + max([transit_nodes['node_id'].astype(int).max(), road_nodes['node_id'].astype(int).max()]) + 1
    transit_nodes.node_id = transit_nodes.node_id.astype(str)

    # Update node_id in the transit_links dataframe for from nodes and to nodes
    # Merge on the original node ID and retain the new node ID by overwriting the from/to node ID columns
    transit_links = transit_links.merge(transit_nodes[['orig_node_id', 'node_id']], left_on='from_node_id',
                                        right_on='orig_node_id', how='left')
    transit_links = transit_links.drop(columns=['from_node_id']).rename(columns={'node_id':'from_node_id'}).drop(columns=['orig_node_id'])
    
    transit_links = transit_links.merge(transit_nodes[['orig_node_id', 'node_id']], left_on='to_node_id',
                                        right_on='orig_node_id', how='left')
    transit_links = transit_links.drop(columns=['to_node_id']).rename(columns={'node_id':'to_node_id'}).drop(columns=['orig_node_id'])
    
    # Remove rows with blank values in from_node_id
    if sum(transit_links['from_node_id'].isna()) > 0:
        logger.warning('{} entries in from_node_id field of transit link CSV are blank. Removing the corresponding rows.'.format(sum(transit_links['from_node_id'].isna())))
        transit_links = transit_links[transit_links['from_node_id'].notna()]

    # Remove rows with blank values in to_node_id
    if sum(transit_links['to_node_id'].isna()) > 0:
        logger.warning('{} entries in to_node_id field of transit link CSV are blank. Removing the corresponding rows.'.format(sum(transit_links['to_node_id'].isna())))
        transit_links = transit_links[transit_links['to_node_id'].notna()]

    # Writing renumbered dataframes to CSV files to be read in by transit_overlay method
    transit_nodes.to_csv(os.path.join(output_dir, 'transit_node_temp.csv'), index=False)
    transit_links.to_csv(os.path.join(output_dir, 'transit_link_temp.csv'), index=False)
    
    # Create road nodes dataframe structure to match transit nodes dataframe
    temp_road_nodes = road_nodes.copy()
    temp_road_nodes['orig_node_id'] = temp_road_nodes['node_id']
    
    # Concatenate road and transit nodes corrected for duplicates
    node_df = pd.concat([temp_road_nodes, transit_nodes], ignore_index=True)
    
    node_df['node_type'] = np.where(node_df['node_type'].isin(['rail_station', 'metro_station', 'stop']), 'transit boarding', node_df['node_type'])
    node_df['node_type'] = np.where(node_df['node_type'].str.endswith("service_node"), 'transit', node_df['node_type'])
    node_df.to_csv(os.path.join(output_dir, 'combined_node.csv'), index=False)
    
    # Transit overlay tool creates buffer polygons around transit nodes and overlays with TAZ polygons
    # If any overlay, segments are created between transit node and centroid connector
    # Outputs a transit_cc_link.csv file in the output directory specified in config file
    transit_overlay(cfg, logger)

    # Path to transit centroid connector CSV file
    # Link CSV file should contain all transit centroid connector links (is created by transit_overlay method above)
    transit_cc_links = pd.read_csv(os.path.join(output_dir, 'transit_cc_link.csv'), skip_blank_lines=True,
                                   usecols=['link_id', 'from_node_id', 'to_node_id', 'directed', 'length', 'facility_type',
                                            'capacity', 'free_speed', 'lanes'],
                                   converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, 'directed': int,
                                               'length': float, 'facility_type': str, 'capacity': float, 'free_speed': float,
                                               'lanes': int})
    
    # Add rows to align with transit links dataframe
    road_links['orig_df'] = 'road_links'
    road_links['link_type'] = 0
    road_links['geometry_id'] = ''
    transit_links['orig_df'] = 'transit_links'
    transit_cc_links['orig_df'] = 'transit_cc_links'
    transit_cc_links['link_type'] = 0
    transit_cc_links['geometry_id'] = ''

    link_df = pd.concat([road_links, transit_links, transit_cc_links], ignore_index=True)

    # Renumber link_id in case of duplicates but keep original link id in new field
    link_df['orig_link_id'] = link_df['link_id']
    link_df['link_id'] = np.arange(len(link_df)) + 1
    link_df['allowed_uses'] = 'c'
    # Note: Does not catch any blank values in from_node_id or to_node_id columns of road network
    link_df.to_csv(os.path.join(output_dir, 'combined_link.csv'), index=False,
                   columns=['link_id', 'from_node_id', 'to_node_id', 'directed', 'length', 'lanes',
                            'facility_type', 'capacity', 'free_speed', 'allowed_uses', 'geometry_id',
                            'link_type', 'orig_link_id', 'orig_df'])
    
    if create_gpkg:
        new_transit_links = link_df[link_df['orig_df'] == 'transit_links']
        new_transit_links.loc[:, 'geometry_id'] = new_transit_links['geometry_id'].astype('str')
        
        # Drop links where geometry_id == 0
        if any(new_transit_links['geometry_id'] == '0'):
            orig = new_transit_links.index.size
            new_transit_links = new_transit_links.drop(index=new_transit_links.loc[new_transit_links['geometry_id'] == '0',].index)
            logger.info('{} records dropped from {} where geometry_id (shape_id) == 0 when creating transit network GPKG.'.format(orig - new_transit_links.index.size, transit_link_csv))

        transit_link_gis_csv = os.path.join(output_dir, 'transit_link_gis.csv')
        new_transit_links.to_csv(transit_link_gis_csv, index=False,
                                 columns=['link_id', 'from_node_id', 'to_node_id', 'directed', 'length', 'lanes',
                                          'facility_type', 'capacity', 'free_speed', 'allowed_uses', 'geometry_id',
                                          'link_type', 'orig_link_id', 'orig_df'])

        transit_node_gis_csv = os.path.join(output_dir, 'transit_node_gis.csv')
        transit_nodes.to_csv(transit_node_gis_csv, index=False,
                             columns=['node_id', 'x_coord', 'y_coord', 'node_type', 'orig_node_id'])
        
        # Create a GPKG of transit links consistent with renumbered link_id and node_id for transit network
        gdb_path = gtfs_linear_referencing_process.create_transit_links_gdb(cfg['GTFS_folder'], output_dir, transit_link_gis_csv, transit_node_gis_csv, logger)
        logger.info("Created transit link GPKG at {}".format(gdb_path))

    end_time = datetime.datetime.now()
    total_run_time = end_time - start_time
    logger.info("Total run time: {}".format(total_run_time))
    logger.info("Prepare RDR transit network helper tool run complete.")


if __name__ == "__main__":
    main()