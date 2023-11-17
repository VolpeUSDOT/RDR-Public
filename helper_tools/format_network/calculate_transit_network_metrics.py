import sys
import os
import argparse
import numpy as np
import pandas as pd
import network_config_reader

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'metamodel_py'))
import rdr_supporting

VERSION_NUMBER = "2023.2"
VERSION_DATE = "11/15/2023"
# ---------------------------------------------------------------------------------------------------
# The following code calculates travel time and toll fields for a network link CSV input file
# based on user parameters and network node/link input CSV files
# ---------------------------------------------------------------------------------------------------


def main():

    # PARSE ARGS
    # ----------------------------------------------------------------------------------------------

    program_description = 'Resilience Disaster Recovery Calculate Network Metrics Helper Tool: ' \
                          + VERSION_NUMBER + ", (" + VERSION_DATE + ")"

    help_text = """
    The command-line input expected for this script is as follows:

    TheFilePathOfThisScript ConfigFilePath
    """

    parser = argparse.ArgumentParser(description=program_description, usage=help_text)

    parser.add_argument("config_file", help="The full path to the XML Scenario", type=str)

    if len(sys.argv) == 2:
        args = parser.parse_args()
    else:
        parser.print_help()
        sys.exit()

    # ---------------------------------------------------------------------------------------------------
    # SETUP
    if not os.path.exists(args.config_file):
        print("ERROR: config file {} can't be found!".format(args.config_file))
        sys.exit()

    cfg = network_config_reader.read_network_config_file(args.config_file)

    # Log files for this helper tool are put in the output dir
    run_name = cfg['run_id']
    output_dir = cfg['output_dir']

    # Set up logging
    logger = rdr_supporting.create_loggers(output_dir, 'calculate_network_metrics', cfg)

    logger.info("=========================================================================")
    logger.info("============ CALCULATE TRAVEL TIME AND TOLL STARTING ====================")
    logger.info("=========================================================================")

    logger.info("Starting calculate travel time and toll helper tool run...")

    # Main code
    # Cases: road links for car owners, road links for TNC users, transit links for all trips

    # Path to comprehensive network node CSV file
    # Required fields are node_id, x_coord, y_coord, node_type
    # Node type field should be clearly specified as one of the following: centroid, road intersection, transit boarding, transit
    node_csv = cfg['node_csv']
    if not os.path.exists(node_csv):
        logger.error('The network node CSV file ' + node_csv + ' does not exist')
        raise Exception("NODE CSV FILE ERROR: input node_csv {} can't be found".format(node_csv))
    df_node = pd.read_csv(node_csv, skip_blank_lines=True,
                          usecols=['node_id', 'node_type'],
                          converters={'node_id': int, 'node_type': str})

    # Path to comprehensive network link CSV file
    # Required fields are link_id, from_node_id, to_node_id, directed, length (miles), facility_type, capacity, free_speed (mph), lanes, allowed_uses
    # Helper tool will overwrite this file with added fields: toll (cents), travel_time (minutes), toll_nocar (cents, optional), travel_time_nocar (minutes, optional)
    link_csv = cfg['link_csv']
    if not os.path.exists(link_csv):
        logger.error('The network link CSV file ' + link_csv + ' does not exist')
        raise Exception("LINK CSV FILE ERROR: input link_csv {} can't be found".format(link_csv))
    df_link = pd.read_csv(link_csv, skip_blank_lines=True,
                          converters={'link_id': int, 'from_node_id': int, 'to_node_id': int, 'directed': int,
                                      'length': float, 'facility_type': str, 'capacity': float, 'free_speed': float,
                                      'lanes': int, 'allowed_uses': str})

    # Merge node type
    df_link = pd.merge(df_link, df_node, how='left', left_on='from_node_id', right_on='node_id', indicator=True)
    logger.debug(("Number of from_node_id not matched to node table: {}".format(sum(df_link['_merge'] == 'left_only'))))
    df_link.drop(labels=['node_id', '_merge'], axis=1, inplace=True)
    df_link.rename({'node_type': 'from_node_type'}, axis='columns', inplace=True)

    df_link = pd.merge(df_link, df_node, how='left', left_on='to_node_id', right_on='node_id', indicator=True)
    logger.debug(("Number of to_node_id not matched to node table: {}".format(sum(df_link['_merge'] == 'left_only'))))
    df_link.drop(labels=['node_id', '_merge'], axis=1, inplace=True)
    df_link.rename({'node_type': 'to_node_type'}, axis='columns', inplace=True)

    # Formulas:
    # Toll for all trips - add centroid connector added cost to all centroid connectors
    # Toll for all trips - if transit is TRUE, add transit cost to boarding links
    # Toll for no car owners - if no car is TRUE, add TNC charge to non-transit/cc links as per-mile
    # and add TNC fixed charge to road cc links
    # Travel time for all trips - calculate free-flow travel time from length and free speed
    # Travel time for all trips - set travel time on transit boarding/transfer links to corresponding wait time
    # Travel time for no car owners - if no car is TRUE, add TNC wait time to road cc links

    # If toll column already exists, assume it contains road tolls only; otherwise create a toll column
    if 'toll' in df_link.columns:
        df_link['toll'] = df_link['toll'].astype(float)
    else:
        df_link['toll'] = 0.0

    # Create (or overwrite) travel time column
    if 'travel_time' in df_link.columns:
        logger.warning("Overwriting previous 'travel_time' column in link CSV")
    if sum(df_link['free_speed'] == 0) > 0:
        logger.warning("Check free_speed field for zero values. Causing NaN values in travel_time field calculation")
    df_link['travel_time'] = np.where(df_link['free_speed'] == 0, np.NaN, 60 * df_link['length'] / df_link['free_speed'])

    # Centroid connector added cost
    df_link['toll'] = np.where((df_link['from_node_type'] == 'centroid') | (df_link['to_node_type'] == 'centroid'),
                               df_link['toll'] + cfg['centroid_connector_cost'], df_link['toll'])

    ### TRANSIT ###
    if cfg['include_transit']:
        df_link['boarding_ind'] = np.where((df_link['from_node_type'] == 'transit boarding') & (df_link['to_node_type'] == 'transit'),
                                           1, 0)

        # Transit fare
        df_link['toll'] = np.where(df_link['boarding_ind'] == 1, df_link['toll'] + cfg['transit_fare'], df_link['toll'])

        # Bus wait time
        df_link['travel_time'] = np.where((df_link['boarding_ind'] == 1) & (df_link['facility_type'] == '603'),
                                          df_link['travel_time'] + cfg['bus_wait_time'], df_link['travel_time'])

        # Tram/subway/rail wait time
        df_link['travel_time'] = np.where((df_link['boarding_ind'] == 1) & (df_link['facility_type'].isin(['600', '601', '602'])),
                                          df_link['travel_time'] + cfg['subway_wait_time'], df_link['travel_time'])

        df_link.drop(labels=['boarding_ind'], axis=1, inplace=True)

    ### TNC ###
    if cfg['include_nocar']:
        # Create toll_nocar and travel_time_nocar fields
        df_link['toll_nocar'] = df_link['toll']
        df_link['travel_time_nocar'] = df_link['travel_time']

        # TNC initial charge
        df_link['toll_nocar'] = np.where((df_link['from_node_type'] == 'centroid') & (~df_link['to_node_type'].isin(['transit boarding', 'transit'])),
                                         df_link['toll_nocar'] + cfg['tnc_initial_cost'], df_link['toll_nocar'])

        # TNC cost per mile
        df_link['toll_nocar'] = np.where((~df_link['facility_type'].isin(['100', '101', '102', '103', '600', '601', '602', '603', '700', '701', '702', '703', '801', '903'])) & ((df_link['from_node_type'] == 'road intersection') | (df_link['to_node_type'] == 'road intersection')),
                                         df_link['toll_nocar'] + cfg['tnc_cost_per_mile'] * df_link['length'],
                                         df_link['toll_nocar'])

        # TNC wait time
        df_link['travel_time_nocar'] = np.where((df_link['from_node_type'] == 'centroid') & (~df_link['to_node_type'].isin(['transit boarding', 'transit'])),
                                                df_link['travel_time_nocar'] + cfg['tnc_wait_time'], df_link['travel_time_nocar'])

    df_link.drop(labels=['from_node_type', 'to_node_type'], axis=1, inplace=True)

    output_link_csv = os.path.join(output_dir, 'link_final.csv')
    if os.path.exists(output_link_csv):
        logger.warning('Overwriting link CSV file at {}'.format(output_link_csv))
    # Copy the filtered df to the final output CSV
    df_link.to_csv(output_link_csv, index=False)

    logger.info("Finished calculate travel time and toll helper tool run")


# ---------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    main()

