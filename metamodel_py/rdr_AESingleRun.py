#!/usr/bin/env python
# coding: utf-8


import os
import numpy as np
import pandas as pd
import geopandas as gpd
import openmatrix as omx
import sqlite3
import shutil
from scipy import stats
from shapely import wkt


def run_AESingleRun(run_params, input_folder, output_folder, cfg, logger):
    logger.info("Start: AequilibraE single run module")
    mtx_fldr = 'matrices'

    # TrueShape.csv path, later used to check for existence of TrueShape.csv
    true_shape_file = os.path.join(input_folder, 'LookupTables', 'TrueShape.csv')

    # Coordinate reference system
    crs = cfg['crs']
    
    # run_params is a dictionary containing the parameters defining a single AequilibraE run
    # run_params['socio'] = 'base'  # string, e.g., 'base', 'urban', 'suburban', 'water'
    # run_params['projgroup'] = '04'  # string, e.g., '04', '30'
    # run_params['resil'] = 'no'  # string, e.g., 'no' for baseline or 'Proj01'
    # run_params['elasticity'] = -1  # non-positive float, e.g., 0, -0.5, -1
    # run_params['hazard'] = '100yr3SLR'  # string, e.g., '100yr3SLR'
    # run_params['recovery'] = '0'  # string, e.g., X ft of exposure to subtract for intermediate recovery stage
    # run_params['run_minieq'] = 1  # possibilities: 0 or 1
    # run_params['matrix_name'] = 'matrix'  # possibilities: 'matrix' or 'nocar'

    logger.config("running AequilibraE with run parameter: socio = {}".format(run_params['socio']))
    logger.config("running AequilibraE with run parameter: projgroup = {}".format(run_params['projgroup']))
    logger.config("running AequilibraE with run parameter: resil = {}".format(run_params['resil']))
    logger.config("running AequilibraE with run parameter: elasticity = {}".format(run_params['elasticity']))
    logger.config("running AequilibraE with run parameter: hazard = {}".format(run_params['hazard']))
    logger.config("running AequilibraE with run parameter: recovery = {}".format(run_params['recovery']))
    logger.config("running AequilibraE with run parameter: run_minieq = {}".format(run_params['run_minieq']))
    logger.config("running AequilibraE with run parameter: matrix_name = {}".format(run_params['matrix_name']))

    elasname = str(int(10 * -run_params['elasticity']))

    # to avoid issues with a set of runs going past midnight, using cfg['run_id'] in folder name instead of date
    basescenname = run_params['socio'] + run_params['projgroup']
    if run_params['socio'] == 'baseyear':
        base_run_folder = os.path.join(output_folder, 'aeq_runs_base_year', 'base',
                                       str(cfg['run_id']), basescenname, run_params['matrix_name'])
    elif run_params['socio'] == 'baseline_run':
        base_run_folder = os.path.join(output_folder, 'aeq_runs_baseline', 'base',
                                       str(cfg['run_id']), basescenname, run_params['matrix_name'])
    else:
        base_run_folder = os.path.join(output_folder, 'aeq_runs', 'base',
                                       str(cfg['run_id']), basescenname, run_params['matrix_name'])

    if run_params['socio'] != 'baseline_run':
        disruptscenname = (basescenname + '_' + run_params['resil'] + '_' + elasname + '_' + run_params['hazard'] +
                           '_' + run_params['recovery'])
        if run_params['socio'] == 'baseyear':
            disrupt_run_folder = os.path.join(output_folder, 'aeq_runs_base_year', 'disrupt',
                                              str(cfg['run_id']), disruptscenname, run_params['matrix_name'])
        else:
            disrupt_run_folder = os.path.join(output_folder, 'aeq_runs', 'disrupt',
                                              str(cfg['run_id']), disruptscenname, run_params['matrix_name'])

        # check if AequilibraE run has already been done successfully (look for NetSkim.csv output) for this run ID
        if os.path.exists(os.path.join(disrupt_run_folder, 'NetSkim.csv')):
            logger.info("AequilibraE run for {} already done for this run ID, skipping run".format(disrupt_run_folder))
            return

    # create OMX file if CSV (or CSVs) are provided instead of OMX
    demand_folder = os.path.join(input_folder, 'AEMaster', mtx_fldr)
    demand_file = os.path.join(demand_folder, run_params['socio'] + '_demand_summed.omx')
    if not os.path.exists(demand_file):
        logger.info("No OMX file detected for demand scenario {}. Reading from CSV to create OMX matrix.".format(run_params['socio']))
        demand_csv_file = os.path.join(demand_folder, run_params['socio'] + '_demand_summed.csv')
        nocar_demand_csv_file = os.path.join(demand_folder, run_params['socio'] + '_demand_summed_nocar.csv')
        if not os.path.exists(demand_csv_file):
            logger.error("DEMAND CSV FILE ERROR: {} could not be found".format(demand_csv_file))
            raise Exception("DEMAND CSV FILE ERROR: {} could not be found".format(demand_csv_file))
        demand_csv_to_omx(demand_folder, run_params['socio'], demand_csv_file, nocar_demand_csv_file, cfg, logger)

    # BASE NETWORK RUN #
    # ----------------------------------------------------------------

    # check if base network run was unsuccessful (look for sp_{basescenname}.omx output) for this set of run parameters
    if not os.path.exists(os.path.join(base_run_folder, mtx_fldr, 'sp_' + basescenname + '.omx')):
        # set up directory structure for AequilibraE run
        network_db = setup_run_folder(run_params, input_folder, base_run_folder, logger)

        # create base network csv file
        create_network_link_csv('base', run_params, input_folder, base_run_folder, cfg, logger)

        # open output_network_fullfile as pandas data frame, strip whitespace from headers
        output_network_table = 'Group' + run_params['projgroup'] + '_baserun'
        output_network_fullfile = os.path.join(base_run_folder, output_network_table + '.csv')
        if not os.path.exists(output_network_fullfile):
            logger.error("BASE NETWORK CSV FILE ERROR: {} could not be found".format(output_network_fullfile))
            raise Exception("BASE NETWORK CSV FILE ERROR: {} could not be found".format(output_network_fullfile))
        logger.info("GMNS_link table to be filled from {}".format(output_network_fullfile))
        base_network = pd.read_csv(output_network_fullfile)
        base_network.columns = base_network.columns.str.strip()

        # SQLite code to create base network link table
        with sqlite3.connect(network_db) as db_con:
            # use to_sql to import base_network as table named output_network_table
            # NOTE for to_sql: "Legacy support is provided for sqlite3.Connection objects."
            base_network.to_sql('GMNS_link', db_con, if_exists='replace', index=False)
            db_cur = db_con.cursor()

            # create links table
            sql1 = "delete from links;"
            db_cur.execute(sql1)
            sql2 = """insert into links(ogc_fid, link_id, a_node, b_node, direction, distance, modes,
                    link_type, capacity_ab, speed_ab, free_flow_time, toll, alpha, beta)
                    select link_id, link_id, from_node_id, to_node_id, directed, length, allowed_uses,
                    facility_type, capacity, free_speed, travel_time, toll, alpha, beta
                    from GMNS_link
                    where GMNS_link.link_available > 0
                    ;"""
            db_cur.execute(sql2)
            sql3 = "update links set capacity_ba = 0, speed_ba = 0"
            db_cur.execute(sql3)

        from rdr_AERouteBase import run_aeq_base
        run_aeq_base(run_params, base_run_folder, cfg, logger)

        link_flow_file = os.path.join(base_run_folder, 'link_flow_' + basescenname + '.csv')
        link_flows = merge_network_outputs(run_params, base_run_folder, output_network_fullfile, link_flow_file, logger)
        if os.path.exists(true_shape_file):
            create_gis_output(run_params, input_folder, base_run_folder, link_flows, logger, crs)

    if run_params['socio'] != 'baseline_run':
        # DISRUPTED NETWORK RUN #
        # ----------------------------------------------------------------

        # set up directory structure for AequilibraE run
        network_db = setup_run_folder(run_params, input_folder, disrupt_run_folder, logger)

        # copy over base network run outputs, 'sp_{basescenname}.omx' and 'rt_{basescenname}.omx'
        base_run_skims = os.path.join(base_run_folder, mtx_fldr, 'sp_' + basescenname + '.omx')
        base_run_assignment = os.path.join(base_run_folder, mtx_fldr, 'rt_' + basescenname + '.omx')
        if not os.path.exists(base_run_skims):
            logger.error("BASE SKIMS FILE ERROR: {} could not be found".format(base_run_skims))
            raise Exception("BASE SKIMS FILE ERROR: {} could not be found".format(base_run_skims))
        if not os.path.exists(base_run_assignment):
            logger.error("BASE ASSIGNMENT FILE ERROR: {} could not be found".format(base_run_assignment))
            raise Exception("BASE ASSIGNMENT FILE ERROR: {} could not be found".format(base_run_assignment))

        # calculate link availability for the disrupted network
        calc_link_availability(run_params, input_folder, disrupt_run_folder, cfg, logger)

        # create disrupted network csv file
        create_network_link_csv('disrupt', run_params, input_folder, disrupt_run_folder, cfg, logger)

        # open output_network_fullfile as pandas data frame, strip whitespace from headers
        output_network_table = ('Group' + run_params['projgroup'] + '_' + run_params['resil'] +
                                '_' + run_params['hazard'] + '_' + run_params['recovery'])
        output_network_fullfile = os.path.join(disrupt_run_folder, output_network_table + '.csv')
        if not os.path.exists(output_network_fullfile):
            logger.error("DISRUPT NETWORK CSV FILE ERROR: {} could not be found".format(output_network_fullfile))
            raise Exception("DISRUPT NETWORK CSV FILE ERROR: {} could not be found".format(output_network_fullfile))
        disrupt_network = pd.read_csv(output_network_fullfile)
        disrupt_network.columns = disrupt_network.columns.str.strip()

        # SQLite code to create disrupted network link table
        with sqlite3.connect(network_db) as db_con:
            # use to_sql to import disrupt_network as table named output_network_table
            # NOTE for to_sql: "Legacy support is provided for sqlite3.Connection objects."
            disrupt_network.to_sql('GMNS_link', db_con, if_exists='replace', index=False)
            db_cur = db_con.cursor()

            # create links table
            sql1 = "delete from links;"
            db_cur.execute(sql1)
            sql2 = """insert into links(ogc_fid, link_id, a_node, b_node, direction, distance, modes, link_type,
                    capacity_ab, speed_ab, free_flow_time, toll, alpha, beta)
                    select link_id, link_id, from_node_id, to_node_id, directed, length, allowed_uses,
                    facility_type, capacity, free_speed, travel_time, toll, alpha, beta
                    from GMNS_link where GMNS_link.link_available > 0;"""
            db_cur.execute(sql2)
            sql3 = "update links set capacity_ba = 0, speed_ba = 0"
            db_cur.execute(sql3)

        from rdr_AERouteDisruptMiniEquilibrium import run_aeq_disrupt_miniequilibrium
        run_aeq_disrupt_miniequilibrium(run_params, base_run_folder, disrupt_run_folder, cfg, logger)

        link_flow_file = os.path.join(disrupt_run_folder, 'link_flow_adjdem_' + disruptscenname + '.csv')
        link_flows = merge_network_outputs(run_params, disrupt_run_folder, output_network_fullfile, link_flow_file, logger)
        if os.path.exists(true_shape_file):
            create_gis_output(run_params, input_folder, disrupt_run_folder, link_flows, logger, crs)

    logger.info("Finished: AequilibraE single run module")


# ==============================================================================


def merge_network_outputs(run_params, output_folder, network_file, flow_file, logger):
    logger.info("Start: merge core model outputs")

    links = pd.read_csv(network_file, converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, 'wkt': str})
    flows = pd.read_csv(flow_file, usecols=['link_id', 'matrix_ab', 'matrix_ba', 'matrix_tot'],
                        converters={'link_id': str, 'matrix_ab': float, 'matrix_ba': float, 'matrix_tot': float})
    links = pd.merge(links, flows, how="left", left_on="link_id", right_on="link_id")
    links = links.assign(vcr = lambda x: np.where(x['capacity'] == 0, 99999, x['matrix_ab'] / x['capacity']))
    links = links.rename(columns={'matrix_ab': 'link_flow_ab', 'matrix_ba': 'link_flow_ba', 'matrix_tot': 'link_flow_total'})
    combined_file = os.path.join(output_folder, 'link_flow_full.csv')
    links.to_csv(combined_file, index=False)

    logger.info("Finished: merge core model outputs")

    return links


# ==============================================================================


def create_gis_output(run_params, input_folder, output_folder, link_flows, logger, crs):
    # This function converts a specified link_flows_full CSV to a GIS-compatible GeoJSON object
    # Inputs:
    # input_folder = input data directory (e.g., 'C:\GitHub\RDR\scenarios\qs1_sioux_falls\Data\inputs')
    # output_folder = AequilibraE run directory (e.g., 'C:\GitHub\RDR\scenarios\qs1_sioux_falls\Data\generated_files\aeq_runs\base\QS1\base02\matrix')
    # link_flows = DataFrame of joined network link attributes and link flows

    # Links
    # Set geometry column from wkt column
    link_flows['geometry'] = link_flows['wkt'].apply(wkt.loads)

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(link_flows, crs=crs)
    gdf = gdf.to_crs('epsg:4326')

    # Export to GeoJSON
    gdf.to_file(os.path.join(output_folder, 'link_flow_full.json'), driver="GeoJSON")

    # Nodes
    nodes_csv = os.path.join(input_folder, 'Networks', 'node.csv')
    node_data = pd.read_csv(nodes_csv, usecols=['node_id', 'x_coord', 'y_coord', 'node_type'],
                            converters={'node_id': str, 'x_coord': float, 'y_coord': float, 'node_type': str})
    node_data['geometry'] = gpd.points_from_xy(node_data.x_coord, node_data.y_coord, crs='epsg:4326')

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(node_data, crs='epsg:4326')

    # Export to GeoJSON
    gdf.to_file(os.path.join(output_folder, 'node.json'), driver="GeoJSON")


# ==============================================================================


def calc_link_availability(run_params, input_folder, output_folder, cfg, logger):
    logger.debug(("start: calculate link availability for hazard = {}, ".format(run_params['hazard']) +
                  "recovery = {}, resil = {}, socio = {}, projgroup = {}".format(run_params['recovery'], run_params['resil'],
                                                                                 run_params['socio'], run_params['projgroup'])))

    project_table = os.path.join(input_folder, 'LookupTables', 'project_table.csv')
    if not os.path.exists(project_table):
        logger.error("PROJECT TABLE FILE ERROR: {} could not be found".format(project_table))
        raise Exception("PROJECT TABLE FILE ERROR: {} could not be found".format(project_table))

    model_params_file = os.path.join(input_folder, 'Model_Parameters.xlsx')
    if not os.path.exists(model_params_file):
        logger.error("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
        raise Exception("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))

    hazard_events = pd.read_excel(model_params_file, sheet_name='Hazards', usecols=['Hazard Event', 'Filename'],
                                  converters={'Hazard Event': str, 'Filename': str})
    # look up corresponding filename for exposure input file from hazards list
    filename = hazard_events.loc[hazard_events['Hazard Event'] == run_params['hazard'], 'Filename'].dropna().tolist()[0]
    exposure_table = os.path.join(input_folder, 'Hazards', str(filename) + '.csv')
    if not os.path.exists(exposure_table):
        logger.error("EXPOSURE TABLE FILE ERROR: {} could not be found".format(exposure_table))
        raise Exception("EXPOSURE TABLE FILE ERROR: {} could not be found".format(exposure_table))

    network_table = os.path.join(input_folder, 'Networks', run_params['socio'] + run_params['projgroup'] + '.csv')
    if not os.path.exists(network_table):
        logger.error("NETWORK TABLE FILE ERROR: {} could not be found".format(network_table))
        raise Exception("NETWORK TABLE FILE ERROR: {} could not be found".format(network_table))

    # table mapping resilience project to network links
    # link availability for resilience project network links depends on mitigation impact
    # options are 'binary' (default), 'manual'
    # if resil mitigation approach is manual, read in Exposure Reduction field as well
    # if a cell in Exposure Reduction field is left blank assume no reduction on the link
    resil_mitigation_approach = cfg['resil_mitigation_approach']
    logger.config("{} resilience project mitigation approach to be used".format(resil_mitigation_approach))
    if resil_mitigation_approach == 'binary':
        projects = pd.read_csv(project_table, usecols=['Project ID', 'link_id'],
                               converters={'Project ID': str, 'link_id': str})
        # NOTE: use 99999 to denote complete mitigation
        projects['Exposure Reduction'] = 99999.0
    elif resil_mitigation_approach == 'manual':
        projects = pd.read_csv(project_table, usecols=['Project ID', 'link_id', 'Exposure Reduction'],
                               converters={'Project ID': str, 'link_id': str, 'Exposure Reduction': float})
    else:
        logger.error("Invalid option selected for resilience mitigation approach.")
        raise Exception("Variable resil_mitigation_approach must be set to 'binary' or 'manual'.")

    # catch any empty values in Exposure Reduction field and set to 0 reduction
    projects['Exposure Reduction'] = projects['Exposure Reduction'].fillna(0)
    projects.drop_duplicates(subset=['Project ID', 'link_id'], inplace=True, ignore_index=True)

    # table with exposure levels for a particular hazard event
    exposures = pd.read_csv(exposure_table, usecols=['link_id', 'from_node_id', 'to_node_id', cfg['exposure_field']],
                            converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, cfg['exposure_field']: float})
    exposures.drop_duplicates(subset=['link_id'], inplace=True, ignore_index=True)
    # catch any empty values in exposure field and set to 0 exposure
    exposures[cfg['exposure_field']] = exposures[cfg['exposure_field']].fillna(0)

    # table with facility types for each network link
    network_links = pd.read_csv(network_table, usecols=['link_id', 'facility_type'],
                                converters={'link_id': str, 'facility_type': str})

    logger.debug("Size of project table: {}".format(projects.shape))
    logger.debug("Size of exposure table: {}".format(exposures.shape))
    logger.debug("Size of network link table: {}".format(network_links.shape))

    recovery_depth = int(run_params['recovery'])

    np_disrupt = exposures.copy(deep=True)
    num_rows = np_disrupt.shape[0]

    # merge in facility_type from network link table
    np_disrupt = pd.merge(np_disrupt, network_links, how='left', on=['link_id'], indicator=True)
    logger.debug(("Number of network links not found in network table: {}".format(sum(np_disrupt['_merge'] == 'left_only'))))
    if np_disrupt.shape[0] != num_rows:
        logger.error(("TABLE JOIN ERROR: Join of exposure table with network link table " +
                      "resulted in duplicate rows. Check that link_id in network link table is unique."))
        raise Exception(("TABLE JOIN ERROR: Join of exposure table with network link table " +
                         "resulted in duplicate rows. Check that link_id in network link table is unique."))
    np_disrupt.drop(labels=['_merge'], axis=1, inplace=True)

    # zone connector network links defined as having at least one centroid node
    np_disrupt['ZoneConn'] = np.where((np_disrupt['from_node_id'].astype(int) < cfg['zone_conn']) | (np_disrupt['to_node_id'].astype(int) < cfg['zone_conn']), 1, 0)

    # convert any string in 'Project ID' column to 1 and NaN to 0 in new 'VulProject' column
    np_disrupt = pd.merge(np_disrupt, projects.loc[projects['Project ID'] == run_params['resil'],
                                                   ['Project ID', 'link_id', 'Exposure Reduction']],
                          how='left', on=['link_id'])
    # links not associated with resilience project do not have Exposure Reduction
    np_disrupt['Exposure Reduction'] = np.where(np_disrupt['Project ID'].isna(), 0, np_disrupt['Exposure Reduction'])
    np_disrupt['VulProject'] = np.where(np_disrupt['Project ID'].isna(), 0, 1)
    logger.debug("Number of links designated zone connectors: {}".format(sum(np_disrupt['ZoneConn'] == 1)))
    logger.debug("Number of links associated with resilience project {}: {}".format(run_params['resil'],
                                                                                    sum(np_disrupt['VulProject'] == 1)))

    # (1) calculate exposure level with recovery_depth
    logger.debug("calculating link availability")
    np_disrupt['recov_value'] = np_disrupt[cfg['exposure_field']] - recovery_depth
    np_disrupt.loc[np_disrupt['recov_value'] < 0, ['recov_value']] = 0

    # (2) update exposure values for network links associated with the resilience project
    logger.debug("applying resilience project exposure reduction")
    np_disrupt['recov_value'] = np_disrupt['recov_value'] - np_disrupt['Exposure Reduction']
    np_disrupt.loc[np_disrupt['recov_value'] < 0, ['recov_value']] = 0

    # (3) calculate 'link_available' column based on recov_value and link_availability_approach
    # exposure level to link availability functionality taken from exposure_grid_overlay.py helper tool
    # potential options are 'binary', 'default_flood_exposure_function', 'manual', 'beta_distribution_function'
    link_availability_approach = cfg['link_availability_approach']
    logger.config("{} link availability approach to be used".format(link_availability_approach))

    if link_availability_approach == 'binary':
        # Use binary case where if 'recov_value' > 0 then 'link_available' = 0, else 'link_available' = 1
        np_disrupt['link_available'] = np.where(np_disrupt['recov_value'] > 0, 0, 1)

    if link_availability_approach == 'default_flood_exposure_function':
        exposure_unit = cfg['exposure_unit']
        # Use default flood exposure function which is based on a depth-damage function defined by Pregnolato et al.
        # in which the maximum safe vehicle speed reaches 0 at a depth of water of approximately 300 millimeters
        # A linear relationship is assumed for link availability when water depths are between 0 and 300 millimeters

        # Convert exposure units to millimeters
        if exposure_unit.lower() in ['feet', 'ft', 'foot']:
            np_disrupt['link_available'] = 1 - (np_disrupt['recov_value'] * 304.8 / 300)
        if exposure_unit.lower() in ['yards', 'yard']:
            np_disrupt['link_available'] = 1 - (np_disrupt['recov_value'] * 914.4 / 300)
        if exposure_unit.lower() in ['meters', 'm']:
            np_disrupt['link_available'] = 1 - (np_disrupt['recov_value'] * 1000 / 300)

        np_disrupt.loc[np_disrupt['link_available'] < 0, ['link_available']] = 0

    if link_availability_approach == 'manual':
        link_availability_csv = cfg['link_availability_csv']
        if not os.path.exists(link_availability_csv):
            logger.error("LINK AVAILABILITY FILE ERROR: {} could not be found".format(link_availability_csv))
            raise Exception("LINK AVAILABILITY FILE ERROR: {} could not be found".format(link_availability_csv))
        # Set up default link availability to avoid key error
        np_disrupt['link_available'] = None
        # Use manual approach where a user-defined CSV lists the range of values and the link availability associated
        # with each range
        # Minimum (inclusive) and maximum (exclusive) value must be defined for each range
        # Read through the CSV
        # for line in CSV
        with open(link_availability_csv, 'r') as rf:
            line_num = 1
            for line in rf:
                if line_num > 1:
                    csv_row = line.rstrip('\n').split(',')
                    min = float(csv_row[0])
                    max = float(csv_row[1])
                    np_disrupt['link_available'] = np.where((np_disrupt['recov_value'] >= min) &
                                                            (np_disrupt['recov_value'] < max),
                                                            csv_row[2], np_disrupt['link_available'])
                line_num += 1
        # Set to fully available if the value is not in the table
        np_disrupt['link_available'] = np_disrupt['link_available'].fillna(1)

    if link_availability_approach == 'facility_type_manual':
        link_availability_csv = cfg['link_availability_csv']
        if not os.path.exists(link_availability_csv):
            logger.error("LINK AVAILABILITY FILE ERROR: {} could not be found".format(link_availability_csv))
            raise Exception("LINK AVAILABILITY FILE ERROR: {} could not be found".format(link_availability_csv))
        # Set up default link availability to avoid key error
        np_disrupt['link_available'] = None
        # Use manual approach where a user-defined CSV lists the range of values and the link availability associated
        # with each range for every facility type
        # Minimum (inclusive) and maximum (exclusive) value must be defined for each range
        # Read through the CSV
        # for line in CSV
        with open(link_availability_csv, 'r') as rf:
            line_num = 1
            for line in rf:
                if line_num > 1:
                    csv_row = line.rstrip('\n').split(',')
                    # fac_type should be str
                    fac_type = csv_row[0]
                    min = float(csv_row[1])
                    max = float(csv_row[2])
                    np_disrupt['link_available'] = np.where((np_disrupt['facility_type'] == fac_type) &
                                                            (np_disrupt['recov_value'] >= min) &
                                                            (np_disrupt['recov_value'] < max),
                                                            csv_row[3], np_disrupt['link_available'])
                line_num += 1
        # Set to fully available if the value is not in the table
        np_disrupt['link_available'] = np_disrupt['link_available'].fillna(1)

    if link_availability_approach == 'beta_distribution_function':
        alpha = cfg['alpha']
        beta = cfg['beta']
        lower_bound = cfg['lower_bound']
        upper_bound = cfg['upper_bound']
        beta_method = cfg['beta_method']
        # Use beta distribution function
        if beta_method == 'lower cumulative':
            np_disrupt['link_available'] = np.where(np_disrupt['recov_value'] < lower_bound, 0,
                                                    np.where(np_disrupt['recov_value'] > upper_bound, 1,
                                                             (stats.beta.cdf(np_disrupt['recov_value'], alpha, beta,
                                                                             loc=lower_bound,
                                                                             scale=upper_bound - lower_bound))))
        elif beta_method == 'upper cumulative':
            np_disrupt['link_available'] = np.where(np_disrupt['recov_value'] < lower_bound, 1,
                                                    np.where(np_disrupt['recov_value'] > upper_bound, 0,
                                                             (1 - (stats.beta.cdf(np_disrupt['recov_value'], alpha,
                                                                                  beta, loc=lower_bound,
                                                                                  scale=upper_bound - lower_bound)))))

    # (4) ensure 'link_available' values equal 1 for network links associated with the resilience project in binary case
    # or network links given value 99999 for Exposure Reduction in manual case
    if resil_mitigation_approach == 'binary':
        # Use binary case where if link is associated with resilience project then 'link_available' = 1
        np_disrupt['link_available'] = np.where(np_disrupt['VulProject'] == 1, 1, np_disrupt['link_available'])
    elif resil_mitigation_approach == 'manual':
        # For manual case if link is assigned 99999 by user then 'link_available' = 1
        np_disrupt['link_available'] = np.where(np_disrupt['Exposure Reduction'] == 99999.0, 1,
                                                np_disrupt['link_available'])

    # (5) after calculating generic link availability, update 'link_available' values for zone connector network links
    # zone connector network links are not disrupted by hazard events
    np_disrupt['link_available'] = np.where(np_disrupt['ZoneConn'] == 1, 1, np_disrupt['link_available'])

    logger.debug(("Number of 'link_available' values " +
                  "missing: {}".format(np_disrupt[np_disrupt['link_available'].isnull()].shape[0])))
    logger.debug("Size of np_disrupt table: {}".format(np_disrupt.shape))

    if np_disrupt.shape[0] != num_rows:
        logger.warning(("Table joins to calculate link availability not unique for " +
                        "hazard = {}, recovery = {}, resil = {}".format(run_params['hazard'], run_params['recovery'],
                                                                        run_params['resil'])))

    output_disrupt_file = os.path.join(output_folder, ('NP_Disrupt_' + run_params['resil'] + '_' +
                                                       run_params['hazard'] + '_' + run_params['recovery'] + '.csv'))

    with open(output_disrupt_file, "w", newline='') as f:
        np_disrupt.to_csv(f, index=False)
        logger.result("Link availability table for disrupted network written to {}".format(output_disrupt_file))

    logger.debug(("finished: calculate link availability for " +
                  "hazard = {}, recovery = {}, resil = {}".format(run_params['hazard'], run_params['recovery'],
                                                                  run_params['resil'])))


# ==============================================================================


def create_network_link_csv(run_type, run_params, input_folder, output_folder, cfg, logger):
    logger.debug(("start: create {} network csv file for ".format(run_type) +
                  "hazard = {}, recovery = {}, socio = {}, ".format(run_params['hazard'], run_params['recovery'], run_params['socio']) +
                  "projgroup = {}, resil = {}, trip table = {}".format(run_params['projgroup'], run_params['resil'], run_params['matrix_name'])))

    # inputs are GMNS-formatted network file, true shapes file (optional),
    # and link availability file from calc_link_availability (if run_type = 'disrupt')
    projgroup_network_table = os.path.join(input_folder, 'Networks', (run_params['socio'] + run_params['projgroup'] +
                                                                      '.csv'))
    if not os.path.exists(projgroup_network_table):
        logger.error("NETWORK FILE ERROR: {} could not be found".format(projgroup_network_table))
        raise Exception("NETWORK FILE ERROR: {} could not be found".format(projgroup_network_table))

    if run_type == 'disrupt':
        link_avail_table = os.path.join(output_folder, ('NP_Disrupt_' + run_params['resil'] +
                                                        '_' + run_params['hazard'] +
                                                        '_' + run_params['recovery'] + '.csv'))
        if not os.path.exists(link_avail_table):
            logger.error("LINK AVAILABILITY FILE ERROR: {} could not be found".format(link_avail_table))
            raise Exception("LINK AVAILABILITY FILE ERROR: {} could not be found".format(link_avail_table))

    if run_type == 'base':
        output_network_file = 'Group' + run_params['projgroup'] + '_baserun.csv'
    elif run_type == 'disrupt':
        output_network_file = ('Group' + run_params['projgroup'] + '_' + run_params['resil'] + '_' +
                               run_params['hazard'] + '_' + run_params['recovery'] + '.csv')
    else:
        logger.error("create_network_link_csv method requires 'base' or 'disrupt' for run_type variable.")
        raise Exception("Invalid option for variable run_type in create_network_link_csv method.")
    output_network_fullfile = os.path.join(output_folder, output_network_file)

    logger.debug("loading input files and look-up tables")

    if run_params['matrix_name'] == 'matrix':
        network = pd.read_csv(projgroup_network_table,
                              usecols=['link_id', 'from_node_id', 'to_node_id', 'directed', 'length', 'facility_type',
                                       'capacity', 'free_speed', 'lanes', 'allowed_uses', 'toll', 'travel_time'],
                              converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, 'directed': int,
                                          'length': float, 'facility_type': str, 'capacity': float, 'free_speed': float,
                                          'lanes': int, 'allowed_uses': str, 'toll': float, 'travel_time': float})
    elif run_params['matrix_name'] == 'nocar':
        network = pd.read_csv(projgroup_network_table,
                              usecols=['link_id', 'from_node_id', 'to_node_id', 'directed', 'length', 'facility_type',
                                       'capacity', 'free_speed', 'lanes', 'allowed_uses', 'toll_nocar', 'travel_time_nocar'],
                              converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, 'directed': int,
                                          'length': float, 'facility_type': str, 'capacity': float, 'free_speed': float,
                                          'lanes': int, 'allowed_uses': str, 'toll_nocar': float, 'travel_time_nocar': float})
        network.rename({'toll_nocar': 'toll', 'travel_time_nocar': 'travel_time'}, axis='columns', inplace=True)
    else:
        logger.error("create_network_link_csv method requires 'matrix' or 'nocar' for matrix_name variable in run_params.")
        raise Exception("Invalid option for variable matrix_name in run_params in create_network_link_csv method.")
    logger.debug("Size of input project group network table: {}".format(network.shape))

    if run_type == 'disrupt':
        availabilities = pd.read_csv(link_avail_table, usecols=['link_id', 'link_available'],
                                     converters={'link_id': str, 'link_available': float})
        # catch any empty fields and set to 0 link availability
        availabilities['link_available'] = availabilities['link_available'].fillna(0)
        logger.debug("Size of input link availability table: {}".format(availabilities.shape))

    true_shape_file = os.path.join(input_folder, 'LookupTables', 'TrueShape.csv')
    if not os.path.exists(true_shape_file):
        logger.warning("TRUE SHAPE FILE WARNING: {} could not be found (optional). Process will continue without this file."
                       .format(true_shape_file))
    else:
        true_shape_table = pd.read_csv(true_shape_file, usecols=['link_id', 'WKT'],
                                       converters={'link_id': str, 'WKT': str})
        true_shape_table.drop_duplicates(inplace=True, ignore_index=True)
        logger.debug("Size of look-up table for wkt: {}".format(true_shape_table.shape))

    # create links input table for AequilibraE from base GMNS links file
    logger.debug("creating {} network links input file for AequilibraE run".format(run_type))
    output_links = network.copy(deep=True)
    num_rows = output_links.shape[0]

    # wkt = look up in true_shape_table if it exists
    # NOTE: not inserted into final links table, but found in output csv file and initial SQL table
    if not os.path.exists(true_shape_file):
        output_links['WKT'] = ""
    else:
        output_links = pd.merge(output_links, true_shape_table, how='left', on=['link_id'], indicator=True)
        logger.debug(("Number of links not found in true shape " +
                      "look-up table: {}".format(sum(output_links['_merge'] == 'left_only'))))
        if sum(output_links['_merge'] == 'left_only') == output_links.shape[0]:
            logger.warning("TABLE JOIN WARNING: Join of AequilibraE links input file with true shape table failed to produce any matches.")
        output_links.drop(labels=['_merge'], axis=1, inplace=True)

    # link_available = look up 'link_available' in availabilities table if run_type = 'disrupt',
    # set to 1 if run_type = 'base'
    # NOTE: not inserted into final links table, but found in output csv file and initial SQL table
    # NOTE: NaN is replaced with 0.999, as in NetworkPrep XLSX workbook
    link_unavailable_default = 0.999
    logger.config(("NaN values in 'link_available' column of AequilibraE links input file are replaced " +
                   "by {} (hard-coded).".format(link_unavailable_default)))
    if run_type == 'base':
        output_links['link_available'] = 1
    elif run_type == 'disrupt':
        output_links = pd.merge(output_links, availabilities, how='left', on=['link_id'], indicator=True)
        logger.debug(("Number of links not found in link availability " +
                      "table: {}".format(sum(output_links['_merge'] == 'left_only'))))
        if sum(output_links['_merge'] == 'left_only') == output_links.shape[0]:
            logger.error(("TABLE JOIN ERROR: Join of AequilibraE links input file with link availability table " +
                         "failed to produce any matches. Check the corresponding table columns."))
            raise Exception(("TABLE JOIN ERROR: Join of AequilibraE links input file with link availability table " +
                             "failed to produce any matches. Check the corresponding table columns."))
        output_links.drop(labels=['_merge'], axis=1, inplace=True)
        output_links['link_available'] = np.where(output_links['link_available'].isna(), link_unavailable_default,
                                                  output_links['link_available'])

    # adjust capacity for disruption, multiply by 'link_available' and 'lanes'
    # GMNS capacity is in veh/day/lane, while AequilibraE capacity is in veh/day
    output_links['capacity'] = output_links['capacity'] * output_links['lanes'] * output_links['link_available']

    # travel_time is taken directly from network file as it may incorporate user-defined wait times
    # free_flow_time (min) = 60 * length / free_speed
    # output_links['free_flow_time'] = 60 * output_links['length'] / output_links['free_speed']
    # toll adjustments to free flow travel time are handled by AequilibraE
    # travel_cost = travel_time + toll / value_of_time is handled by AequilibraE

    # volume-delay function parameters are specified by link type in an optional input file
    link_types_file = os.path.join(input_folder, 'LookupTables', 'link_types_table.csv')
    if not os.path.exists(link_types_file):
        # default values for alpha and beta parameters are 0.15 and 4
        output_links['alpha'] = 0.15
        output_links['beta'] = 4
    else:
        # NOTE: link types table has required fields 'facility_type', 'alpha', 'beta'
        link_types_table = pd.read_csv(link_types_file, usecols=['facility_type', 'alpha', 'beta'],
                                       converters={'facility_type': str, 'alpha': float, 'beta': float})
        logger.debug("Size of link types look-up table: {}".format(link_types_table.shape))
        output_links = pd.merge(output_links, link_types_table, how='left', on=['facility_type'], indicator=True)
        logger.debug("Number of links found in link types table: {}".format(sum(output_links['_merge'] == 'both')))
        if sum(output_links['_merge'] == 'left_only') == output_links.shape[0]:
            logger.warning("TABLE JOIN WARNING: Join of AequilibraE links input file with link types table failed to produce any matches.")
        output_links.drop(labels=['_merge'], axis=1, inplace=True)
        # default values for alpha and beta parameters are 0.15 and 4
        output_links['alpha'] = output_links['alpha'].fillna(0.15)
        output_links['beta'] = output_links['beta'].fillna(4)

    output_links.rename({'WKT': 'wkt'}, axis='columns', inplace=True)

    logger.debug("Size of network links table for AequilibraE run: {}".format(output_links.shape))
    if output_links.shape[0] != num_rows:
        logger.warning(("Table joins to create network csv file not unique for " +
                        "hazard = {}, recovery = {}, socio = {}, ".format(run_params['hazard'], run_params['recovery'],
                                                                          run_params['socio']) +
                        "projgroup = {}, resil = {}".format(run_params['projgroup'], run_params['resil'])))

    with open(output_network_fullfile, "w", newline='') as f:
        output_links.to_csv(f, index=False, columns=['link_id', 'from_node_id', 'to_node_id', 'directed', 'length',
                                                     'facility_type', 'capacity', 'free_speed', 'lanes', 'allowed_uses',
                                                     'travel_time', 'toll', 'alpha', 'beta', 'link_available',
                                                     'wkt'])
        logger.result("AequilibraE network links table written to {}".format(output_network_fullfile))

    logger.debug(("finished: create {} network csv file for ".format(run_type) +
                  "hazard = {}, recovery = {}, socio = {}, ".format(run_params['hazard'], run_params['recovery'], run_params['socio']) +
                  "projgroup = {}, resil = {}, trip table = {}".format(run_params['projgroup'], run_params['resil'], run_params['matrix_name'])))


# ==============================================================================


# create a directory for the AequilibraE run with the correct file structure, a copy of project_database.sqlite,
# and a demand table (omx file)
def setup_run_folder(run_params, input_folder, run_folder, logger):
    logger.debug("start: set up AequilibraE run directory")
    mtx_fldr = 'matrices'

    # check if run_folder exists (in case of a previously aborted run) and if so then delete run_folder directory tree
    if os.path.exists(run_folder):
        logger.warning(("Directory {} already exists (e.g., due to prior incomplete run), removing existing files and re-running".format(run_folder)))
        shutil.rmtree(run_folder)

    logger.debug("creating directory {} for AequilibraE run".format(run_folder))
    master_folder = os.path.join(input_folder, 'AEMaster')
    if not os.path.exists(master_folder):
        logger.error("AEQ DIRECTORY ERROR: AEMaster folder {} could not be found".format(master_folder))
        raise Exception("AEQ DIRECTORY ERROR: AEMaster folder {} could not be found".format(master_folder))

    shutil.copytree(master_folder, run_folder, ignore=shutil.ignore_patterns('*.omx'))

    # copy over demand omx file for correct 'socio'
    demand_file = os.path.join(master_folder, mtx_fldr, run_params['socio'] + '_demand_summed.omx')
    if not os.path.exists(demand_file):
        logger.error("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
        raise Exception("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
    shutil.copy2(demand_file, os.path.join(run_folder, mtx_fldr))

    network_db = os.path.join(run_folder, 'project_database.sqlite')

    logger.debug("finished: set up AequilibraE run directory, returned path to project_database.sqlite database")
    return network_db


# ==============================================================================


def create_matrix(output_folder, socio, trip_csv_file, output_matrixname, f_output, matrix_size, logger):
    if output_matrixname == 'matrix':
        debug_filename = os.path.join(output_folder, socio + '_debug_demand.csv')
    elif output_matrixname == 'nocar':
        debug_filename = os.path.join(output_folder, socio + '_debug_demand_nocar.csv')

    # Read a flat file trip table into pandas dataframe
    # Presuming we have a long-format CSV file
    df_trip = pd.read_csv(trip_csv_file, header=0)
    df_trip.astype({'trips': 'float'}).dtypes
    logger.debug(df_trip.head())
    logger.debug("The trip table file {} has size {} by {}".format(trip_csv_file, str(df_trip.shape[0]), str(df_trip.shape[1])))
    logger.debug("Total number of trips: {}".format(str(df_trip['trips'].sum())))

    # Sanity check: Number of rows in df_trip can be at most matrix_size * matrix_size
    matrix_size_squared = matrix_size * matrix_size
    logger.debug("Rows in trip_csv_file: {}. Matrix size square: {}.".format(str(df_trip.shape[0]), str(matrix_size_squared)))
    if (df_trip.shape[0] > matrix_size_squared):
        logger.error("Error: Number of rows in the CSV file exceeds matrix size squared!")
        raise Exception("Error: Number of rows in the CSV file exceeds matrix size squared!")
    # Assuming we have an O-D format trip type
    pivot = df_trip.pivot(index='orig_node', columns='dest_node', values='trips')
    pivotnp = pivot.to_numpy()
    pivotnp = np.nan_to_num(pivotnp, nan=0)
    f_output[output_matrixname] = pivotnp  # Put the filled-in matrix into the OMX file
    pivot.to_csv(debug_filename, index=True)

    return


# ==============================================================================


def demand_csv_to_omx(demand_folder, socio, trip_csv_file, no_car_csv_file, cfg, logger):
    node_csv_file = os.path.join(cfg['input_dir'], 'Networks', 'node.csv')
    outfile = os.path.join(demand_folder, socio + '_demand_summed.omx')

    # Read the nodes file into a dataframe
    df_node = pd.read_csv(node_csv_file, header=0)
    logger.debug(df_node.head())

    # Set up the dictionary of centroids
    # Assumption: node_type = 'centroid' for centroid nodes in nodes file
    # Centroid nodes are the lowest numbered nodes, provided at the beginning of the list of nodes, but node numbers need not be consecutive
    tazdictrow = {}
    centroid_index = 0
    for index in df_node.index:
        if df_node['node_type'][index] == 'centroid':
            tazdictrow[df_node['node_id'][index]] = centroid_index
            centroid_index = centroid_index + 1
    taz_list = list(tazdictrow.keys())  # This is the taz mapping that will be used when building the OMX matrix file
    matrix_size = len(tazdictrow)  # Should match the number of nodes flagged as centroids
    logger.debug("Total number of centroids: {}".format(str(matrix_size)))
    highest_centroid_node_number = max(tazdictrow, key=tazdictrow.get)
    logger.debug("Highest centroid node is {}".format(str(highest_centroid_node_number)))

    # Set up the OMX output
    f_output = omx.open_file(outfile, 'w')
    f_output.create_mapping('taz', taz_list)  # Set up the TAZ mapping
    # Write the dataframe to an OMX file
    # This makes use of tazdictrow and matrix_size that was established earlier
    # The rows are also written to a file that is used for debugging

    create_matrix(cfg['output_dir'], socio, trip_csv_file, "matrix", f_output, matrix_size, logger)

    if os.path.exists(no_car_csv_file):
        create_matrix(cfg['output_dir'], socio, no_car_csv_file, "nocar", f_output, matrix_size, logger)

    f_output.close()  # Close the OMX file
