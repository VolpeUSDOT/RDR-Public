# ----------------------------------------------------------------------------------------------------
# The following code executes two core model runs to measure TAZ-to-TAZ trip metrics (e.g., skims)
# for a baseline "no action" scenario and a resilience project scenario for a particular hazard,
# socioeconomic future, and elasticity. Users can use this tool to analyze the impact of a specific
# resilience project on trips taken between TAZs in the user's network, as identified by a categorical
# or continuous TAZ-level metric.
# ----------------------------------------------------------------------------------------------------

import sys
import os
import sqlite3
import pandas as pd
import openmatrix as omx
import subprocess
from itertools import product
import shutil

# Import code from benefits_analysis_config_reader.py for read_benefits_analysis_config_file method
import benefits_analysis_config_reader

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'metamodel_py'))
import rdr_AESingleRun
import rdr_setup
import rdr_supporting

VERSION_NUMBER = "2025.1"
VERSION_DATE = "6/20/2025"

def main():

    # ---------------------------------------------------------------------------------------------
    # SETUP
    # Read TAZ metrics config file, which has the path to main RDR config file
    program_name = os.path.basename(__file__)

    if len(sys.argv) != 2:
        print("usage: " + program_name + " <full_path_to_config_file>")
        sys.exit()

    full_path_to_config_file = sys.argv[1]

    if not os.path.exists(full_path_to_config_file):
        print("ERROR: config file {} can't be found!".format(full_path_to_config_file))
        sys.exit()

    TAZ_metrics_cfg = benefits_analysis_config_reader.read_benefits_analysis_config_file(full_path_to_config_file)

    # Values from TAZ metrics config file
    output_dir = TAZ_metrics_cfg['benefits_analysis_dir']
    run_id = TAZ_metrics_cfg['run_id']
    rdr_cfg_path = TAZ_metrics_cfg['path_to_RDR_config_file']

    # Set up logging and report run start time
    logger = rdr_supporting.create_loggers(output_dir, 'TAZ_metrics', TAZ_metrics_cfg)

    logger.info("==============================================================================")
    logger.info("================= GENERATING MODEL RUNS FOR TAZ METRICS ======================")
    logger.info("==============================================================================")

    logger.info("Reading in RDR config file")
    error_list, cfg = rdr_setup.read_config_file(rdr_cfg_path, 'config')

    # The helper tool requires AequilibraE inputs from the main RDR input directory input_dir
    # Logs and the benefits analysis core model outputs are stored in the benefits analysis output directory output_dir
    input_dir = cfg['input_dir']

    logger.info("Starting TAZ metrics run...")
    logger.info("Checking required inputs for TAZ metrics run")

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
                                                   converters={'Project Groups': str, 'Project ID': str})
                projgroup_to_resil = projgroup_to_resil.rename(columns={'Project ID': 'Resiliency Projects'})
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: ProjectGroups tab is missing required columns"
                logger.error(error_text)
            else:
                # Confirm resilience project and project group match
                try:
                    assert(TAZ_metrics_cfg['projgroup'] == projgroup_to_resil.loc[projgroup_to_resil['Resiliency Projects'] == TAZ_metrics_cfg['resil'], 'Project Groups'][0])
                except:
                    error_text = "MODEL PARAMETERS FILE ERROR: Resilience project and project group specified in TAZ metrics config file do not match"
                    logger.error(error_text)
                    error_list.append(error_text)

    # Resilience projects files
    # 1) Is project_table.csv file present
    # 2) Check that project_table.csv has columns link_id, Project ID, Category; Exposure Reduction must be float if exists
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
                # Test Exposure Reduction can be converted to float
                try:
                    project_table['Exposure Reduction'] = pd.to_numeric(project_table['Exposure Reduction'], downcast='float')
                except:
                    error_text = "RESILIENCE PROJECTS FILE ERROR: Column Exposure Reduction could not be converted to float in project table input file"
                    logger.error(error_text)
                    error_list.append(error_text)

                # Confirm resilience project is included in project table
                try:
                    assert(sum(project_table['Project ID'] == TAZ_metrics_cfg['resil']) > 0)
                except:
                    error_text = "RESILIENCE PROJECTS FILE ERROR: Resilience project in TAZ metrics config file not found in project table input file"
                    logger.error(error_text)
                    error_list.append(error_text)
    else:
        error_text = "RESILIENCE PROJECTS FOLDER ERROR: LookupTables directory for resilience projects files does not exist"
        logger.error(error_text)
        error_list.append(error_text)

    # Exposure analysis files
    # For hazard in TAZ metrics config file:
    # 1) Is there a hazard CSV file
    # 2) Check that link_id, from_node_id, to_node_id, Value (or similar) exist; from_node_id, to_node_id must be int, Value must be float
    hazard_folder = os.path.join(input_dir, 'Hazards')
    if os.path.isdir(hazard_folder):
        filename = TAZ_metrics_cfg['hazard'] + '.csv'
        f = os.path.join(hazard_folder, filename)

        # CSV STEP 1: Check file exists
        if not os.path.exists(f):
            error_text = "EXPOSURE ANALYSIS FILE ERROR: Exposure analysis input file could not be found"
            logger.error(error_text)
            error_list.append(error_text)
        else:
            # CSV STEP 2: Check file has necessary columns
            try:
                exposures = pd.read_csv(f, usecols=['link_id', 'from_node_id', 'to_node_id', cfg['exposure_field']],
                                        converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, cfg['exposure_field']: str})
            except:
                error_text = "EXPOSURE ANALYSIS FILE ERROR: File for hazard {} is missing required columns".format(TAZ_metrics_cfg['hazard'])
                logger.error(error_text)
                error_list.append(error_text)
            else:
                # Test from_node_id can be converted to int
                try:
                    exposures['from_node_id'] = pd.to_numeric(exposures['from_node_id'], downcast='integer')
                except:
                    error_text = "EXPOSURE ANALYSIS FILE ERROR: Column from_node_id could not be converted to int for hazard {}".format(TAZ_metrics_cfg['hazard'])
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test to_node_id can be converted to int
                try:
                    exposures['to_node_id'] = pd.to_numeric(exposures['to_node_id'], downcast='integer')
                except:
                    error_text = "EXPOSURE ANALYSIS FILE ERROR: Column to_node_id could not be converted to int for hazard {}".format(TAZ_metrics_cfg['hazard'])
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test cfg['exposure_field'] can be converted to float
                try:
                    exposures[cfg['exposure_field']] = pd.to_numeric(exposures[cfg['exposure_field']], downcast='float')
                except:
                    error_text = "EXPOSURE ANALYSIS FILE ERROR: Column specifying exposure level could not be converted to float for hazard {}".format(TAZ_metrics_cfg['hazard'])
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
    # For socio and project group in TAZ metrics config file:
    # 1) Is there a links CSV file
    # 2) Check that link_id, from_node_id, to_node_id, directed, length, facility_type, capacity, free_speed, lanes, allowed_uses, toll, travel_time exist;
    #    from_node_id, to_node_id, directed, lanes must be int, length, capacity, free_speed, toll, travel_time must be float
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
        i = TAZ_metrics_cfg['socio']
        j = TAZ_metrics_cfg['projgroup']
        link_file = i + j + '.csv'
        if not os.path.exists(os.path.join(networks_folder, link_file)):
            error_text = "NETWORK LINK FILE ERROR: No network link file is present for socio {} and project group {} listed in TAZ metrics config file".format(i, j)
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
                omx_demand_file = i + '_demand_summed.omx'
                csv_demand_file = i + '_demand_summed.csv'
                nocar_csv_demand_file = i + '_demand_summed_nocar.csv'
                if not os.path.exists(os.path.join(demand_folder, omx_demand_file)) and not os.path.exists(os.path.join(demand_folder, csv_demand_file)):
                    error_text = "DEMAND FILE ERROR: No demand OMX or CSV file is present for socio {} corresponding to network link file {}".format(i, link_file)
                    logger.error(error_text)
                    error_list.append(error_text)
                else:
                    nocar = False
                    if os.path.exists(os.path.join(demand_folder, omx_demand_file)):
                        omx_file = omx.open_file(os.path.join(demand_folder, omx_demand_file))
                        if 'nocar' in omx_file.list_matrices():
                            nocar = True
                        omx_file.close()
                    elif os.path.exists(os.path.join(demand_folder, nocar_csv_demand_file)):
                        nocar = True

                    if nocar:
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
        error_text = "NETWORK FOLDER ERROR: Networks directory for network attribute files does not exist"
        logger.error(error_text)
        error_list.append(error_text)

    # ---------------------------------------------------------------------------------------------------
    # Demand files
    # For socio listed in TAZ metrics config file:
    # 1) Is there a demand OMX or CSV file
    # 2) If OMX, check file has 'matrix' square demand matrix and 'taz' mapping
    # 3) If 'nocar' trip table matrix, check that it is square
    # 4) If CSV, check that orig_node, dest_node, trips exist; orig_node, dest_node must be int, trips must be float
    demand_folder = os.path.join(input_dir, 'AEMaster', 'matrices')

    if os.path.isdir(demand_folder):
        omx_demand_file = os.path.join(demand_folder, i + '_demand_summed.omx')
        csv_demand_file = os.path.join(demand_folder, i + '_demand_summed.csv')
        nocar_csv_demand_file = os.path.join(demand_folder, i + '_demand_summed_nocar.csv')
        # OMX STEP 1: Check file exists
        if not os.path.exists(omx_demand_file) and not os.path.exists(csv_demand_file):
            error_text = "DEMAND FILE ERROR: No demand OMX or CSV file is present for socio {} listed in TAZ metrics config file".format(i)
            logger.error(error_text)
            error_list.append(error_text)
        else:
            try:
                if os.path.exists(omx_demand_file):
                    omx_file = omx.open_file(omx_demand_file)
                    assert('matrix' in omx_file.list_matrices())
                    assert('taz' in omx_file.list_mappings())
                    matrix_shape = omx_file['matrix'].shape
                    assert(matrix_shape[0] == matrix_shape[1])
                elif os.path.exists(csv_demand_file):
                    trips = pd.read_csv(os.path.join(demand_folder, csv_demand_file),
                                        usecols=['orig_node', 'dest_node', 'trips'],
                                        converters={'orig_node': str, 'dest_node': str, 'trips': str})
                    # Test orig_node and dest_node can be converted to int
                    trips['orig_node'] = pd.to_numeric(trips['orig_node'], downcast='integer')
                    trips['dest_node'] = pd.to_numeric(trips['dest_node'], downcast='integer')
                    # Test trips can be converted to float
                    trips['trips'] = pd.to_numeric(trips['trips'], downcast='float')
            except:
                error_text = "DEMAND FILE ERROR: OMX or CSV file is missing required attributes for socio {}".format(i)
                logger.error(error_text)
                error_list.append(error_text)
            else:
                if os.path.exists(omx_demand_file):
                    if 'nocar' in omx_file.list_matrices():
                        try:
                            matrix_shape = omx_file['nocar'].shape
                            assert(matrix_shape[0] == matrix_shape[1])
                        except:
                            error_text = "DEMAND FILE ERROR: OMX file 'nocar' trip table is not square for socio {}".format(i)
                            logger.error(error_text)
                            error_list.append(error_text)
                    omx_file.close()
                elif os.path.exists(csv_demand_file):
                    if os.path.exists(nocar_csv_demand_file):
                        try:
                            trips = pd.read_csv(os.path.join(demand_folder, nocar_csv_demand_file),
                                                usecols=['orig_node', 'dest_node', 'trips'],
                                                converters={'orig_node': str, 'dest_node': str, 'trips': str})
                            # Test orig_node and dest_node can be converted to int
                            trips['orig_node'] = pd.to_numeric(trips['orig_node'], downcast='integer')
                            trips['dest_node'] = pd.to_numeric(trips['dest_node'], downcast='integer')
                            # Test trips can be converted to float
                            trips['trips'] = pd.to_numeric(trips['trips'], downcast='float')
                        except:
                            error_text = "DEMAND FILE ERROR: CSV file for 'nocar' trip table is missing required attributes for socio {}".format(i)
                            logger.error(error_text)
                            error_list.append(error_text)
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
    # Get run_params from TAZ metrics config file - socio, projgroup, resil, elasticity, hazard
    # Do two AequilibraE runs - one for resil = 'no' and one for resil = project ID

    # Baseline "no action" core model run
    logger.info("Running AequilibraE for the baseline 'no action' scenario")
    run_params = {}
    run_params['socio'] = TAZ_metrics_cfg['socio']
    run_params['projgroup'] = TAZ_metrics_cfg['projgroup']
    run_params['resil'] = TAZ_metrics_cfg['baseline']  # always no for baseline run
    run_params['elasticity'] = TAZ_metrics_cfg['elasticity']
    run_params['hazard'] = TAZ_metrics_cfg['hazard']
    run_params['recovery'] = TAZ_metrics_cfg['recovery']  # always '0' for TAZ metrics runs
    run_params['run_minieq'] = TAZ_metrics_cfg['run_minieq']
    run_params['matrix_name'] = 'matrix'  # always run AequilibraE for the default 'matrix'

    # Method rdr_AESingleRun.run_AESingleRun runs both 'SP' and 'RT'; TAZ metrics notebook uses config file parameter to pull correct skims from outputs
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
    run_params['resil'] = TAZ_metrics_cfg['resil']
    run_params['matrix_name'] = 'matrix'  # always run AequilibraE for the default 'matrix'

    # Method rdr_AESingleRun.run_AESingleRun runs both 'SP' and 'RT'; TAZ metrics notebook uses config file parameter to pull correct skims from outputs
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

    run_notebook(full_path_to_config_file, TAZ_metrics_cfg, logger)

    logger.info("Finished TAZ metrics run")


# ==============================================================================


def run_notebook(full_path_to_config_file, TAZ_metrics_cfg, logger):

    # Values from config file
    output_dir = TAZ_metrics_cfg['benefits_analysis_dir']
    run_id = TAZ_metrics_cfg['run_id']
    TAZ_col_name = TAZ_metrics_cfg['TAZ_col_name']

    category_name = TAZ_metrics_cfg['TAZ_feature']
    category_filename = TAZ_metrics_cfg['TAZ_mapping']

    rdr_cfg_path = TAZ_metrics_cfg['path_to_RDR_config_file']
    resil = TAZ_metrics_cfg['resil']
    baseline = TAZ_metrics_cfg['baseline']
    hazard = TAZ_metrics_cfg['hazard']
    recovery = TAZ_metrics_cfg['recovery']
    socio = TAZ_metrics_cfg['socio']
    projgroup = TAZ_metrics_cfg['projgroup']
    elasticity = TAZ_metrics_cfg['elasticity']
    elasname = str(int(10 * -elasticity))

    if not os.path.exists(rdr_cfg_path):
        logger.error("ERROR: RDR config file {} can't be found!".format(rdr_cfg_path))
        raise Exception("ERROR: RDR config file {} can't be found!".format(rdr_cfg_path))

    # Values from RDR config file
    error_list, cfg = rdr_setup.read_config_file(rdr_cfg_path, 'config')
    RDR_run_id = cfg['run_id']
    input_dir = cfg['input_dir']

    # Check that the TAZ mapping data file specified in the TAZ metrics config exists
    if not os.path.exists(category_filename):
        logger.error('ERROR: {} not found. Please run the TAZ_attribute_overlay first or directly provide your own TAZ mapping data file and specify the filename for it as TAZ_mapping in the TAZ_metrics.config file.'.format(category_filename))
        raise Exception('ERROR: {} not found.'.format(category_filename))

    # Check that the TAZ mapping data are numeric
    taz_attribute = pd.read_csv(category_filename,
                             usecols=[TAZ_col_name, category_name])
    if taz_attribute[category_name].dtype == 'O':
        logger.error("ERROR: Some of the data in {} are not numeric. The TAZ mapping data must be binary, ordinal, or continuous for the current version of this tool.".format(category_filename))
        raise Exception("ERROR: Some of the data in {} are not numeric. The TAZ mapping data must be binary, ordinal, or continuous for the current version of this tool.".format(category_filename))

    # Check for blank values in TAZ mapping category
    if any(pd.isna(taz_attribute[category_name])):
        logger.error("ERROR: TAZ feature column {} in {} contains blank values. Reduce min_percentile_include parameter in TAZ metrics config.".format(category_name, taz_attribute))
        raise Exception("ERROR: TAZ feature column {} in {} contains blank values. Reduce min_percentile_include parameter in TAZ metrics config.".format(category_name, taz_attribute))

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

    # Create a temporary file to store the TAZ metrics configuration file path so that the notebook can access it
    with open('temp.txt', 'w') as f:
        f.write(full_path_to_config_file)

    # Point to categorical or continuous notebook based on the number of unique values in the TAZ mapping variable
    if taz_attribute[category_name].nunique() < 20:
        notebookname = 'MetricsByTAZ_categorical.ipynb'
    else:
        notebookname = 'MetricsByTAZ_continuous.ipynb'

    # Normalize the path for the output directory
    output_dir_norm = os.path.normpath(os.path.join(os.getcwd(), output_dir))

    # Run the notebook
    subprocess.call(['jupyter', 'nbconvert', '--to=html', 
                     '--no-input',
                     '--output-dir=' + output_dir_norm,
                     '--output', 'MetricsByTAZ_' + run_id + '.html',
                     '--execute', notebookname])

    logger.info('Output_dir: {}, run_id: {}, notebookname: {}'.format(output_dir_norm, run_id, notebookname))

    if os.path.exists(os.path.join(output_dir_norm, "MetricsByTAZ_{}.html".format(run_id))):
        logger.info('MetricsByTAZ_{}.html created in {}'.format(run_id, output_dir_norm))
    else:
        logger.error('ERROR: MetricsByTAZ_{}.html not found in {}'.format(run_id, output_dir_norm))

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
                              converters={'node_id': str, 'x_coord': float, 'y_coord': float, 'node_type': str})

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
