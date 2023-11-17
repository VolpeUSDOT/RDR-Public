# ----------------------------------------------------------------------------------------------------
# The following code executes two core model runs to measure TAZ-to-TAZ trip metrics (e.g., skims)
# for a baseline "no action" scenario and a resilience project scenario for a particular hazard,
# socioeconomic future, and elasticity. Users can use this tool to analyze the impact of a specific
# resilience project on trips taken between TAZs in the user's network, as identified by a categorical
# TAZ-level equity metric.
# ----------------------------------------------------------------------------------------------------

import sys
import os
import sqlite3
import pandas as pd
import openmatrix as omx
import subprocess
from itertools import product

# Import code from equity_config_reader.py for read_equity_config_file method
import equity_config_reader

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'metamodel_py'))
import rdr_AESingleRun
import rdr_setup
import rdr_supporting

VERSION_NUMBER = "2023.2"
VERSION_DATE = "11/15/2023"


def main():

    # ---------------------------------------------------------------------------------------------
    # SETUP
    # Read equity config file, which has the path to main RDR config file
    program_name = os.path.basename(__file__)

    if len(sys.argv) != 2:
        print("usage: " + program_name + " <full_path_to_config_file>")
        sys.exit()

    full_path_to_config_file = sys.argv[1]

    if not os.path.exists(full_path_to_config_file):
        print("ERROR: config file {} can't be found!".format(full_path_to_config_file))
        sys.exit()

    equity_cfg = equity_config_reader.read_equity_config_file(full_path_to_config_file)

    # Values from equity config file
    output_dir = equity_cfg['equity_analysis_dir']
    run_id = equity_cfg['run_id']
    rdr_cfg_path = equity_cfg['path_to_RDR_config_file']

    # Set up logging and report run start time
    logger = rdr_supporting.create_loggers(output_dir, 'TAZ_metrics', equity_cfg)

    logger.info("=========================================================================")
    logger.info("=============== GENERATING MODEL RUNS FOR EQUITY ========================")
    logger.info("=========================================================================")

    logger.info("Reading in RDR config file")
    cfg = rdr_setup.read_config_file(rdr_cfg_path)

    # The helper tool requires AequilibraE inputs from the main RDR input directory input_dir
    # Logs and the equity analysis core model outputs are stored in the equity output directory output_dir
    input_dir = cfg['input_dir']

    logger.info("Starting equity metrics run...")
    logger.info("Checking required inputs for equity metrics run")

    # ---------------------------------------------------------------------------------------------
    # INPUT VALIDATION
    # Validating resil, hazard, projgroup, and socio
    # Code below is adapted from rdr_input_validation.py in the helper_tools

    # Create list of input validation errors to put in a log file for users
    # If there is an error, it does not stop checking and just spits them all out at the end
    error_list = []

    # Model_Parameters.xlsx
    # 1) Is it present
    # 2) Check resil and projgroup match

    model_params_file = os.path.join(input_dir, 'Model_Parameters.xlsx')
    # XLSX STEP 1: Check file exists
    if not os.path.exists(model_params_file):
        error_text = "MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file)
        logger.error(error_text)
    else:
        # XLSX STEP 2: Check each tab exists
        try:
            projgroup_to_resil = pd.read_excel(model_params_file, sheet_name='ProjectGroups')
        except:
            error_text = "MODEL PARAMETERS FILE ERROR: ProjectGroups tab could not be found"
            logger.error(error_text)
        else:
            # XLSX STEP 3: Check each tab has necessary columns
            try:
                projgroup_to_resil = pd.read_excel(model_params_file, sheet_name='ProjectGroups',
                                                   converters={'Project Groups': str, 'Resiliency Projects': str})
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: ProjectGroups tab is missing required columns"
                logger.error(error_text)
            else:
                # Confirm resilience project and project group match
                try:
                    assert(equity_cfg['projgroup'] == projgroup_to_resil.loc[projgroup_to_resil['Resiliency Projects'] == equity_cfg['resil'], 'Project Groups'][0])
                except:
                    error_text = "MODEL PARAMETERS FILE ERROR: Resilience project and project group specified in equity config file do not match"
                    logger.error(error_text)
                    error_list.append(error_text)

    # Resilience projects files
    # 1) Is project_table.csv file present
    # 2) Check that project_table.csv has columns link_id, Project ID, Category; link_id must be int, Exposure Reduction must be float if exists
    # 3) Resilience project is included
    resil_folder = os.path.join(input_dir, 'LookupTables')

    if os.path.isdir(resil_folder):
        # CSV STEP 1: Check file exists
        project_table_file = os.path.join(resil_folder, 'project_table.csv')
        if not os.path.exists(project_table_file):
            error_text = "RESILIENCE PROJECTS FILE ERROR: Project table input file could not be found"
            logger.error(error_text)
            error_list.append(error_text)
        else:
            # CSV STEP 2: Check file has necessary columns
            try:
                resil_mitigation_approach = cfg['resil_mitigation_approach']
                if resil_mitigation_approach == 'binary':
                    project_table = pd.read_csv(project_table_file, usecols=['Project ID', 'link_id', 'Category'],
                                                converters={'Project ID': str, 'link_id': str, 'Category': str})
                    # NOTE: use 99999 to create dummy Exposure Reduction column
                    project_table['Exposure Reduction'] = 99999.0
                elif resil_mitigation_approach == 'manual':
                    project_table = pd.read_csv(project_table_file, usecols=['Project ID', 'link_id', 'Category', 'Exposure Reduction'],
                                                converters={'Project ID': str, 'link_id': str, 'Category': str, 'Exposure Reduction': str})
            except:
                error_text = "RESILIENCE PROJECTS FILE ERROR: Project table input file is missing required columns"
                logger.error(error_text)
                error_list.append(error_text)
            else:
                # Test link_id can be converted to int
                try:
                    project_table['link_id'] = pd.to_numeric(project_table['link_id'], downcast='integer')
                except:
                    error_text = "RESILIENCE PROJECTS FILE ERROR: Column link_id could not be converted to int in project table input file"
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test Exposure Reduction can be converted to float
                try:
                    project_table['Exposure Reduction'] = pd.to_numeric(project_table['Exposure Reduction'], downcast='float')
                except:
                    error_text = "RESILIENCE PROJECTS FILE ERROR: Column Exposure Reduction could not be converted to float in project table input file"
                    logger.error(error_text)
                    error_list.append(error_text)

                # Confirm resilience project is included in project table
                try:
                    assert(sum(project_table['Project ID'] == equity_cfg['resil']) > 0)
                except:
                    error_text = "RESILIENCE PROJECTS FILE ERROR: Resilience project in equity config file not found in project table input file"
                    logger.error(error_text)
                    error_list.append(error_text)
    else:
        error_text = "RESILIENCE PROJECTS FOLDER ERROR: LookupTables directory for resilience projects files does not exist"
        logger.error(error_text)
        error_list.append(error_text)

    # Exposure analysis files
    # For hazard in equity config file:
    # 1) Is there a hazard CSV file
    # 2) Check that link_id, A, B, Value (or similar) exist; link_id, A, B must be int, Value must be float
    hazard_folder = os.path.join(input_dir, 'Hazards')
    if os.path.isdir(hazard_folder):
        filename = equity_cfg['hazard'] + '.csv'
        f = os.path.join(hazard_folder, filename)

        # CSV STEP 1: Check file exists
        if not os.path.exists(f):
            error_text = "EXPOSURE ANALYSIS FILE ERROR: Exposure analysis input file could not be found"
            logger.error(error_text)
            error_list.append(error_text)
        else:
            # CSV STEP 2: Check file has necessary columns
            try:
                exposures = pd.read_csv(f, usecols=['link_id', 'A', 'B', cfg['exposure_field']],
                                        converters={'link_id': str, 'A': str, 'B': str, cfg['exposure_field']: str})
            except:
                error_text = "EXPOSURE ANALYSIS FILE ERROR: File for hazard {} is missing required columns".format(equity_cfg['hazard'])
                logger.error(error_text)
                error_list.append(error_text)
            else:
                # Test link_id can be converted to int
                try:
                    exposures['link_id'] = pd.to_numeric(exposures['link_id'], downcast='integer')
                except:
                    error_text = "EXPOSURE ANALYSIS FILE ERROR: Column link_id could not be converted to int for hazard {}".format(equity_cfg['hazard'])
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test A can be converted to int
                try:
                    exposures['A'] = pd.to_numeric(exposures['A'], downcast='integer')
                except:
                    error_text = "EXPOSURE ANALYSIS FILE ERROR: Column A could not be converted to int for hazard {}".format(equity_cfg['hazard'])
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test B can be converted to int
                try:
                    exposures['B'] = pd.to_numeric(exposures['B'], downcast='integer')
                except:
                    error_text = "EXPOSURE ANALYSIS FILE ERROR: Column B could not be converted to int for hazard {}".format(equity_cfg['hazard'])
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test cfg['exposure_field'] can be converted to float
                try:
                    exposures[cfg['exposure_field']] = pd.to_numeric(exposures[cfg['exposure_field']], downcast='float')
                except:
                    error_text = "EXPOSURE ANALYSIS FILE ERROR: Column specifying exposure level could not be converted to float for hazard {}".format(equity_cfg['hazard'])
                    logger.error(error_text)
                    error_list.append(error_text)
    else:
        error_text = "EXPOSURE ANALYSIS FOLDER ERROR: Hazards directory for exposure analysis files does not exist"
        logger.error(error_text)
        error_list.append(error_text)

    # Network attribute files - link and node
    # 1) Is there a node CSV file
    # 2) Check that node_id, x_coord, y_coord, node_type exist; node_id must be int, x_coord, y_coord must be float
    # 3) Check that node_id has no duplicate values
    # For socio and project group in equity config file:
    # 1) Is there a links CSV file
    # 2) Check that link_id, from_node_id, to_node_id, directed, length, facility_type, capacity, free_speed, lanes, allowed_uses, toll, travel_time exist;
    #    link_id, from_node_id, to_node_id, directed, lanes must be int, length, capacity, free_speed, toll, travel_time must be float
    # 3) Check that link_id has no duplicate values
    # 4) Check that directed is always 1, allowed_uses is always c
    # 5) If 'nocar' trip table matrix exists, check that toll_nocar, travel_time_nocar exist; both must be float
    networks_folder = os.path.join(input_dir, 'Networks')

    if os.path.isdir(networks_folder):
        # CSV STEP 1: Check file exists
        node_file = os.path.join(networks_folder, 'node.csv')
        if not os.path.exists(node_file):
            error_text = "NETWORK NODE FILE ERROR: Node input file could not be found"
            logger.error(error_text)
            error_list.append(error_text)
        else:
            # CSV STEP 2: Check file has necessary columns
            try:
                nodes = pd.read_csv(node_file, usecols=['node_id', 'x_coord', 'y_coord', 'node_type'],
                                    converters={'node_id': str, 'x_coord': str, 'y_coord': str, 'node_type': str})
            except:
                error_text = "NETWORK NODE FILE ERROR: Node input file is missing required columns"
                logger.error(error_text)
                error_list.append(error_text)
            else:
                # Test node_id can be converted to int
                try:
                    nodes['node_id'] = pd.to_numeric(nodes['node_id'], downcast='integer')
                except:
                    error_text = "NETWORK NODE FILE ERROR: Column node_id could not be converted to int"
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test node_id is a unique identifier
                try:
                    assert(not nodes.duplicated(subset=['node_id']).any())
                except:
                    error_text = "NETWORK NODE FILE ERROR: Column node_id is not a unique identifier"
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test x_coord can be converted to float
                try:
                    nodes['x_coord'] = pd.to_numeric(nodes['x_coord'], downcast='float')
                except:
                    error_text = "NETWORK NODE FILE ERROR: Column x_coord could not be converted to float"
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test y_coord can be converted to float
                try:
                    nodes['y_coord'] = pd.to_numeric(nodes['y_coord'], downcast='float')
                except:
                    error_text = "NETWORK NODE FILE ERROR: Column y_coord could not be converted to float"
                    logger.error(error_text)
                    error_list.append(error_text)

        # CSV STEP 1: Check file exists
        i = equity_cfg['socio']
        j = equity_cfg['projgroup']
        link_file = i + j + '.csv'
        if not os.path.exists(os.path.join(networks_folder, link_file)):
            error_text = "NETWORK LINK FILE ERROR: No network link file is present for socio {} and project group {} listed in equity config file".format(i, j)
            logger.error(error_text)
            error_list.append(error_text)
        else:
            # CSV STEP 2: Check file has necessary columns
            try:
                links = pd.read_csv(os.path.join(networks_folder, link_file),
                                    usecols=['link_id', 'from_node_id', 'to_node_id', 'directed', 'length', 'facility_type',
                                                'capacity', 'free_speed', 'lanes', 'allowed_uses', 'toll', 'travel_time'],
                                    converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, 'directed': str,
                                                'length': str, 'facility_type': str, 'capacity': str, 'free_speed': str,
                                                'lanes': str, 'allowed_uses': str, 'toll': str, 'travel_time': str})
            except:
                error_text = "NETWORK LINK FILE ERROR: File for socio {} and project group {} is missing required columns".format(i, j)
                logger.error(error_text)
                error_list.append(error_text)
            else:
                # Test link_id can be converted to int
                try:
                    links['link_id'] = pd.to_numeric(links['link_id'], downcast='integer')
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column link_id could not be converted to int for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test link_id is a unique identifier
                try:
                    assert(not links.duplicated(subset=['link_id']).any())
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column link_id is not a unique identifier for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test from_node_id can be converted to int
                try:
                    links['from_node_id'] = pd.to_numeric(links['from_node_id'], downcast='integer')
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column from_node_id could not be converted to int for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test to_node_id can be converted to int
                try:
                    links['to_node_id'] = pd.to_numeric(links['to_node_id'], downcast='integer')
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column to_node_id could not be converted to int for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test directed can be converted to int and is always 1
                try:
                    links['directed'] = pd.to_numeric(links['directed'], downcast='integer')
                    assert(all(links['directed'] == 1))
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column directed must have values of 1 only for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test lanes can be converted to int
                try:
                    links['lanes'] = pd.to_numeric(links['lanes'], downcast='integer')
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column lanes could not be converted to int for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test length can be converted to float
                try:
                    links['length'] = pd.to_numeric(links['length'], downcast='float')
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column length could not be converted to float for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test capacity can be converted to float
                try:
                    links['capacity'] = pd.to_numeric(links['capacity'], downcast='float')
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column capacity could not be converted to float for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test free_speed can be converted to float
                try:
                    links['free_speed'] = pd.to_numeric(links['free_speed'], downcast='float')
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column free_speed could not be converted to float for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test toll can be converted to float
                try:
                    links['toll'] = pd.to_numeric(links['toll'], downcast='float')
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column toll could not be converted to float for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test travel_time can be converted to float
                try:
                    links['travel_time'] = pd.to_numeric(links['travel_time'], downcast='float')
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column travel_time could not be converted to float for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test allowed_uses is always equal to 'c'
                try:
                    assert(all(links['allowed_uses'] == 'c'))
                except:
                    error_text = "NETWORK LINK FILE ERROR: Column allowed_uses must have values 'c' only for socio {} and project group {}".format(i, j)
                    logger.error(error_text)
                    error_list.append(error_text)

                demand_folder = os.path.join(input_dir, 'AEMaster', 'matrices')
                demand_file = i + '_demand_summed.omx'
                if not os.path.exists(os.path.join(demand_folder, demand_file)):
                    error_text = "DEMAND FILE ERROR: No demand OMX file is present for socio {} corresponding to network link file {}".format(i, link_file)
                    logger.error(error_text)
                    error_list.append(error_text)
                else:
                    omx_file = omx.open_file(os.path.join(demand_folder, demand_file))
                    if 'nocar' in omx_file.list_matrices():
                        omx_file.close()
                        try:
                            links = pd.read_csv(os.path.join(networks_folder, link_file),
                                    usecols=['toll_nocar', 'travel_time_nocar'],
                                    converters={'toll': str, 'travel_time': str})
                        except:
                            error_text = "NETWORK LINK FILE ERROR: File for socio {} and project group {} is missing required columns corresponding to no car trip table".format(i, j)
                            logger.error(error_text)
                            error_list.append(error_text)
                        else:
                            # Test toll_nocar can be converted to float
                            try:
                                links['toll_nocar'] = pd.to_numeric(links['toll_nocar'], downcast='float')
                            except:
                                error_text = "NETWORK LINK FILE ERROR: Column toll_nocar could not be converted to float for socio {} and project group {}".format(i, j)
                                logger.error(error_text)
                                error_list.append(error_text)

                            # Test travel_time_nocar can be converted to float
                            try:
                                links['travel_time_nocar'] = pd.to_numeric(links['travel_time_nocar'], downcast='float')
                            except:
                                error_text = "NETWORK LINK FILE ERROR: Column travel_time_nocar could not be converted to float for socio {} and project group {}".format(i, j)
                                logger.error(error_text)
                                error_list.append(error_text)

                    else:
                        omx_file.close()
    else:
        error_text = "NETWORK FOLDER ERROR: Networks directory for network attribute files does not exist"
        logger.error(error_text)
        error_list.append(error_text)

    # ---------------------------------------------------------------------------------------------------
    # Demand files
    # For socio listed in equity config file:
    # 1) Is there a demand OMX file
    # 2) Check OMX file has 'matrix' square demand matrix and 'taz' mapping
    # 3) If 'nocar' trip table matrix, check that it is square
    demand_folder = os.path.join(input_dir, 'AEMaster', 'matrices')

    if os.path.isdir(demand_folder):
        demand_file = os.path.join(demand_folder, i + '_demand_summed.omx')
        # OMX STEP 1: Check file exists
        if not os.path.exists(demand_file):
            error_text = "DEMAND FILE ERROR: No demand OMX file is present for socio {} listed in equity config file".format(i)
            logger.error(error_text)
            error_list.append(error_text)
        else:
            try:
                omx_file = omx.open_file(demand_file)
                assert('matrix' in omx_file.list_matrices())
                assert('taz' in omx_file.list_mappings())
                matrix_shape = omx_file['matrix'].shape
                assert(matrix_shape[0] == matrix_shape[1])
            except:
                error_text = "DEMAND FILE ERROR: OMX file is missing required attributes for socio {}".format(i)
                logger.error(error_text)
                error_list.append(error_text)
            else:
                if 'nocar' in omx_file.list_matrices():
                    try:
                        matrix_shape = omx_file['nocar'].shape
                        assert(matrix_shape[0] == matrix_shape[1])
                    except:
                        error_text = "DEMAND FILE ERROR: OMX file 'nocar' trip table is not square for socio {}".format(i)
                        logger.error(error_text)
                        error_list.append(error_text)
                omx_file.close()
    else:
        error_text = "DEMAND FOLDER ERROR: Matrices directory for demand OMX files does not exist"
        logger.error(error_text)
        error_list.append(error_text)

    # If any check failed, raise exception
    if len(error_list)> 0:
        logger.error(("Exiting script with {} breaking errors found! See logger.error outputs in log file for details. Consult the Run Checklist and User Guide to fix.".format(len(error_list))))
        raise Exception("Exiting script with {} breaking errors found! See logger.error outputs in log file for details. Consult the Run Checklist and User Guide to fix.".format(len(error_list)))
    else:
        logger.info("All input validation checks passed successfully! No errors found.")
    
    # ---------------------------------------------------------------------------------------------
    # SETUP SQLITE NODES DATA
    logger.info("Setting up SQLite database nodes table")
    setup_sql_nodes(input_dir, logger)

    # ---------------------------------------------------------------------------------------------------
    # AEQ SINGLE RUNS
    # Get run_params from equity config file - socio, projgroup, resil, elasticity, hazard
    # Do two AequilibraE runs - one for resil = 'no' and one for resil = project ID

    # Baseline "no action" core model run
    logger.info("Running AequilibraE for the baseline 'no action' scenario")
    run_params = {}
    run_params['socio'] = equity_cfg['socio']
    run_params['projgroup'] = equity_cfg['projgroup']
    run_params['resil'] = equity_cfg['baseline']  # always no for baseline run
    run_params['elasticity'] = equity_cfg['elasticity']
    run_params['hazard'] = equity_cfg['hazard']
    run_params['recovery'] = equity_cfg['recovery']  # always '0' for equity analysis runs
    run_params['run_minieq'] = equity_cfg['run_minieq']
    run_params['matrix_name'] = 'matrix'  # always run AequilibraE for the default 'matrix'

    # Method rdr_AESingleRun.run_AESingleRun runs both 'SP' and 'RT'; equity notebook uses config file parameter to pull correct skims from outputs
    # Determining whether run has already been done takes place within run_AESingleRun method
    rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)

    # Run AequilibraE a second time if a 'nocar' trip table exists
    mtx_fldr = 'matrices'
    demand_file = os.path.join(input_dir, 'AEMaster', mtx_fldr, run_params['socio'] + '_demand_summed.omx')
    if not os.path.exists(demand_file):
        logger.error("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
        raise Exception("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
    f = omx.open_file(demand_file)
    if 'nocar' in f.list_matrices():
        f.close()
        run_params['matrix_name'] = 'nocar'
        # Determining whether run has already been done takes place within run_AESingleRun method
        rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)
    else:
        f.close()

    logger.info("Finished running AequilibraE for baseline 'no action' scenario")

    # Resilience project core model run
    logger.info("Running AequilibraE for the resilience project scenario")
    run_params['resil'] = equity_cfg['resil']
    run_params['matrix_name'] = 'matrix'  # always run AequilibraE for the default 'matrix'

    # Method rdr_AESingleRun.run_AESingleRun runs both 'SP' and 'RT'; equity notebook uses config file parameter to pull correct skims from outputs
    # Determining whether run has already been done takes place within run_AESingleRun method
    rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)

    # Run AequilibraE a second time if a 'nocar' trip table exists
    mtx_fldr = 'matrices'
    demand_file = os.path.join(input_dir, 'AEMaster', mtx_fldr, run_params['socio'] + '_demand_summed.omx')
    if not os.path.exists(demand_file):
        logger.error("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
        raise Exception("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
    f = omx.open_file(demand_file)
    if 'nocar' in f.list_matrices():
        f.close()
        run_params['matrix_name'] = 'nocar'
        # Determining whether run has already been done takes place within run_AESingleRun method
        rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)
    else:
        f.close()

    logger.info("Finished running AequilibraE for resilience project scenario")

    run_notebook(full_path_to_config_file, equity_cfg, logger)

    logger.info("Finished equity metrics run")


# ==============================================================================


def run_notebook(full_path_to_config_file, equity_cfg, logger):
    
    # Values from config file
    output_dir = equity_cfg['equity_analysis_dir']
    run_id = equity_cfg['run_id']
    category_filename = equity_cfg['output_name']
    category_name = equity_cfg['equity_feature']    
    rdr_cfg_path = equity_cfg['path_to_RDR_config_file']
    resil = equity_cfg['resil']
    baseline = equity_cfg['baseline']
    hazard = equity_cfg['hazard']
    recovery = equity_cfg['recovery']
    socio = equity_cfg['socio']
    projgroup = equity_cfg['projgroup']
    elasticity = equity_cfg['elasticity']
    elasname = str(int(10 * -elasticity))

    if not os.path.exists(rdr_cfg_path):
        logger.error("ERROR: RDR config file {} can't be found!".format(rdr_cfg_path))
        raise Exception("ERROR: RDR config file {} can't be found!".format(rdr_cfg_path))

    # Values from RDR config file
    cfg = rdr_setup.read_config_file(rdr_cfg_path)
    RDR_run_id = cfg['run_id']

    # Check that the equity data file specified in the equity config exists
    if not os.path.exists(os.path.join(output_dir, category_filename + '.csv')):
        logger.error('ERROR: {}.csv not found in {}. Please run the equity_overlay first or directly provide your own equity data file and specify the filename for it as output_name in the equity_metrics.config file.'.format(category_filename, output_dir))
        raise Exception('ERROR: {}.csv not found in {}.'.format(category_filename, output_dir))

    # Check that the equity data are numeric
    taz_equity = pd.read_csv(os.path.join(output_dir, category_filename + '.csv'),
                             usecols=['TAZ', category_name])
    if taz_equity[category_name].dtype == 'O':
        logger.error("ERROR: Some of the data in {} are not numeric. The equity data must be binary or ordinal for the current version of this tool.".format(os.path.join(output_dir, category_filename + '.csv')))
        raise Exception("ERROR: Some of the data in {} are not numeric. The equity data must be binary or ordinal for the current version of this tool.".format(os.path.join(output_dir, category_filename + '.csv')))

    # Check for blank values in equity category
    if any(pd.isna(taz_equity[category_name])):
        logger.error("ERROR: Equity feature column {} in {} contains blank values. Reduce min_percentile_include parameter in equity config.".format(category_name, taz_equity))
        raise Exception("ERROR: Equity feature column {} in {} contains blank values. Reduce min_percentile_include parameter in equity config.".format(category_name, taz_equity))

    # Check that AequilibraE parameters that the user entered map to file paths associated with a corresponding RDR run
    # Location of the OMX files for "base"
    omx_folder_path = os.path.join(output_dir, "aeq_runs", "base", RDR_run_id,
                                   socio + projgroup, "matrix", "matrices")
    if not os.path.exists(omx_folder_path):
        logger.error('ERROR: The OMX folder path {} could not be found.'.format(omx_folder_path))
        raise Exception('ERROR: The OMX folder path {} could not be found.'.format(omx_folder_path))  
    # Location of the OMX files for "disruption with resilience investment"
    omx_folder_path = os.path.join(output_dir, "aeq_runs", "disrupt", RDR_run_id,
                                   socio + projgroup + '_' + resil + '_' + elasname + '_' + hazard + '_' + recovery,
                                   "matrix", "matrices")
    if not os.path.exists(omx_folder_path):
        logger.error('ERROR: The OMX folder path {} could not be found.'.format(omx_folder_path))
        raise Exception('ERROR: The OMX folder path {} could not be found.'.format(omx_folder_path))  
    # Location of the OMX files for "disruption WITHOUT resilience investment"
    omx_folder_path = os.path.join(output_dir, "aeq_runs", "disrupt", RDR_run_id,
                                   socio + projgroup + '_' + baseline + '_' + elasname + '_' + hazard + '_' + recovery,
                                   "matrix", "matrices")
    if not os.path.exists(omx_folder_path):
        logger.error('ERROR: The OMX folder path {} could not be found.'.format(omx_folder_path))
        raise Exception('ERROR: The OMX folder path {} could not be found.'.format(omx_folder_path))  

    logger.info("=========================================================================")
    logger.info("=================== RUNNING TAZ REPORT NOTEBOOK =========================")
    logger.info("=========================================================================")

    # Notify user if a prior file will be overwritten
    existingFile = os.path.join(output_dir, 'MetricsByTAZ_' + run_id + '.html')
    if os.path.exists(existingFile):
        logger.warning("An existing file of the same name will be overwritten. A new MetricsByTAZ_{}.html file will be created in {}.".format(run_id, output_dir))

    # Create a temporary file to store the equity configuration file path so that the notebook can access it
    with open('temp.txt', 'w') as f:
        f.write(full_path_to_config_file)

    # Point to categorical or continuous notebook based on the number of unique values in the equity variable
    if taz_equity[category_name].nunique() < 20:
        notebookname = 'MetricsByTAZ_categorical.ipynb'
    else:
        notebookname = 'MetricsByTAZ_continuous.ipynb'

    # Run the notebook
    subprocess.call(['jupyter-nbconvert',
                     '--execute',
                     '--to', 'html',
                     '--output-dir=' + output_dir,
                     '--no-input',
                     '--output', 'MetricsByTAZ_' + run_id + '.html',
                     "--ExecutePreprocessor.kernel_name='python3'",
                     notebookname])

    logger.info("MetricsByTAZ_{}.html created in {}".format(run_id, output_dir))

    # Delete temporary file
    os.remove('temp.txt')


# ==============================================================================


def setup_sql_nodes(input_dir, logger):
    # AequilibraE requires a SQLite database to be setup first--this code is copied from rdr_RunAE.py
    # Set up AEMaster SQLite database with node information
    logger.info("importing node input file into SQLite database")
    node_file = os.path.join(input_dir, 'Networks', 'node.csv')
    network_db = os.path.join(input_dir, 'AEMaster', 'project_database.sqlite')
    if not os.path.exists(node_file):
        logger.error("NODE FILE ERROR: {} could not be found".format(node_file))
        raise Exception("NODE FILE ERROR: {} could not be found".format(node_file))
    elif not os.path.exists(network_db):
        logger.error("SQLITE DB ERROR: {} could not be found".format(network_db))
        raise Exception("SQLITE DB ERROR: {} could not be found".format(network_db))
    else:
        df_node = pd.read_csv(node_file, usecols=['node_id', 'x_coord', 'y_coord', 'node_type'],
                              converters={'node_id': int, 'x_coord': float, 'y_coord': float, 'node_type': str})

        with sqlite3.connect(network_db) as db_con:
            # Use to_sql to import df_node as table named GMNS_node
            # NOTE for to_sql: "Legacy support is provided for sqlite3.Connection objects."
            df_node.to_sql('GMNS_node', db_con, if_exists='replace', index=False)
            db_cur = db_con.cursor()

            # Delete existing nodes table
            sql1 = "delete from nodes;"
            db_cur.execute(sql1)
            # Insert node data into nodes table
            sql2 = """insert into nodes (ogc_fid, node_id, x, y, is_centroid)
                    select node_id, node_id, x_coord, y_coord, case node_type when 'centroid' then 1 else 0 end
                    from GMNS_node
                    order by node_id asc;"""
            db_cur.execute(sql2)


# ==============================================================================


if __name__ == "__main__":
    main()

