# ---------------------------------------------------------------------------------------------------
# Name: rdr_input_validation
#
# Checks existence and contents of necessary input files for an RDR run.
# Does not check batch file, configuration file, or optional input files.
# User needs to provide the configuration file for the RDR run as an input argument.
#
# ---------------------------------------------------------------------------------------------------
import sys
import os
import argparse
import shutil
import logging
import sqlite3
import pandas as pd
import openmatrix as omx
from itertools import product
import numpy as np
import datetime

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'metamodel_py'))
import rdr_setup
import rdr_supporting

VERSION_NUMBER = "2024.2"
VERSION_DATE = "12/16/2024"

# Create function to compute summary statistics of numeric variables to allow user to check 
# whether they are reasonable. Function gets called in the main function a few times and then at the end
# a composite dataframe is concatenated to summarize the statistics for these variables.
def summary_info_by_type(df, ind, val, file, notes):
    stats = pd.pivot_table(data = df, index = ind, aggfunc = {val : ["min", "median", "max"]})
    stats = stats.reset_index()
    stats.columns = stats.columns.get_level_values(1)
    stats.iloc[:,0] = val + " (" + ind + " = " + stats.iloc[:,0] + ")"
    stats = stats.rename(columns = {stats.columns[0]: "parameter"})
    stats.insert(0, 'file', file)
    stats['notes'] = notes
    return stats


# ==============================================================================


def main():

    # ----------------------------------------------------------------------------------------------
    # PARSE ARGS
    program_description = 'Resilience Disaster Recovery Input Validation Helper Tool: ' \
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
    error_list_cfg, cfg = rdr_setup.read_config_file(args.config_file, 'config')

    # Input files validated by this helper tool should be located in the scenario input directory
    input_folder = cfg['input_dir']

    # Logs and validation report will be put in the scenario output directory
    output_folder = cfg['output_dir']

    # Set up logging
    logger = rdr_supporting.create_loggers(output_folder, 'input_validation', cfg)

    logger.info("Starting input validation...")

    # Create list of input validation errors to put in a log file for users
    # If there is an error, it does not stop checking and just spits them all out at the end
    error_list = []
    # Add errors from read_config_file method, if any
    error_list.extend(error_list_cfg)

    # Create a list of dataframes with values to check for reasonableness
    # These dataframes will get concatenated and saved as a CSV file for user review
    param_dfs_list = []
    # List of items not included in the CSV
    excluded_list = []

    # ---------------------------------------------------------------------------------------------------
    # Model_Parameters.xlsx
    # 1) Is it present
    # 2) Does it contain six tabs with required columns

    has_error_model_params = False
    has_error_resil_projects = False
    has_error_hazards = False   

    model_params_file = os.path.join(input_folder, 'Model_Parameters.xlsx')
    # XLSX STEP 1: Check file exists
    if not os.path.exists(model_params_file):
        error_text = "MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file)
        logger.error(error_text)
        error_list.append(error_text)
        has_error_model_params = True
    else:
        # XLSX STEP 2: Check each tab exists (and if so, has necessary columns)
        tabs = ['EconomicScenarios', 'Elasticities', 'ProjectGroups', 'Hazards', 'RecoveryStages', 'FrequencyFactors']
        converters_dict = {'EconomicScenarios' : {'Economic Scenarios': str}, 
                           'Elasticities' : {'Trip Loss Elasticities': str}, 
                           'ProjectGroups' : {'Project Groups': str, 'Project ID': str}, 
                           'Hazards' : {'Hazard Event': str, 'Filename': str, 'HazardDim1': str, 'HazardDim2': str, 'Event Probability in Start Year': str}, 
                           'RecoveryStages' : {'Recovery Stages': str}, 
                           'FrequencyFactors' : {'Event Frequency Factors': str}}
        for t in tabs:
            try:
                model_params = pd.read_excel(model_params_file, sheet_name = t)
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: " + t + " tab could not be found."
                logger.error(error_text)
                error_list.append(error_text)
                has_error_model_params = True

            # XLSX STEP 3: Check it has necessary columns
            else:
                try:
                    model_params = pd.read_excel(model_params_file, sheet_name = t,
                                                 converters = converters_dict[t])
                except:
                    error_text = "MODEL PARAMETERS FILE ERROR: " + t + " tab is missing required columns."
                    logger.error(error_text)
                    error_list.append(error_text)
                    has_error_model_params = True            

        if not(has_error_model_params):
            # Test recovery stages are nonnegative numbers
            try:
                recovery = pd.read_excel(model_params_file, sheet_name='RecoveryStages',
                                         converters={'Recovery Stages': str})

                recovery_num = pd.to_numeric(recovery['Recovery Stages'].dropna(), downcast='float')
                assert(all(recovery_num >= 0))
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: Recovery stages are not all nonnegative numbers"
                logger.error(error_text)
                error_list.append(error_text)

            # Test elasticities can be converted to float
            try:
                model_params = pd.read_excel(model_params_file, sheet_name='Elasticities',
                                             converters={'Trip Loss Elasticities': str})
                                
                model_params['Trip Loss Elasticities'] = pd.to_numeric(model_params['Trip Loss Elasticities'].dropna(), downcast='float')
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: Elasticities could not be converted to float"
                logger.error(error_text)
                error_list.append(error_text)

            # Test event frequency factors are nonnegative numbers
            try:
                model_params = pd.read_excel(model_params_file, sheet_name='FrequencyFactors',
                                             converters={'Event Frequency Factors': str})

                event_frequency = pd.to_numeric(model_params['Event Frequency Factors'].dropna(), downcast='float')
                assert(all(event_frequency >= 0))
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: Event frequency factors are not all nonnegative numbers"
                logger.error(error_text)
                error_list.append(error_text)

            # Confirm no resilience project is assigned to more than one project group
            try:
                projgroup_to_resil = pd.read_excel(model_params_file, sheet_name='ProjectGroups',
                                                   converters={'Project Groups': str, 'Project ID': str})                
                projgroup_to_resil = projgroup_to_resil.rename(columns={'Project ID': 'Resiliency Projects'})

                test_resil_projects = projgroup_to_resil.loc[projgroup_to_resil['Resiliency Projects'] != 'no',
                                                             ['Project Groups', 'Resiliency Projects']].drop_duplicates(ignore_index=True)
                assert(test_resil_projects.groupby(['Resiliency Projects']).size().max() == 1)
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: At least one resilience project assigned to multiple project groups"
                logger.error(error_text)
                error_list.append(error_text)
            
            # Test HazardDim1 can be converted to int
            hazard_events = pd.read_excel(model_params_file, sheet_name='Hazards',
                                          usecols=['Hazard Event', 'Filename', 'HazardDim1', 'HazardDim2', 'Event Probability in Start Year'],
                                          converters={'Hazard Event': str, 'Filename': str, 'HazardDim1': str, 'HazardDim2': str,
                                                      'Event Probability in Start Year': str})
            
            try:
                hazard_events['HazardDim1'] = pd.to_numeric(hazard_events['HazardDim1'], downcast='integer')
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: HazardDim1 column could not be converted to int"
                logger.error(error_text)
                error_list.append(error_text)

            # Test HazardDim2 can be converted to int
            try:
                hazard_events['HazardDim2'] = pd.to_numeric(hazard_events['HazardDim2'], downcast='integer')
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: HazardDim2 column could not be converted to int"
                logger.error(error_text)
                error_list.append(error_text)

            # Test Event Probability in Start Year can be converted to float and is non-negative
            try:
                hazard_events['Event Probability in Start Year'] = pd.to_numeric(hazard_events['Event Probability in Start Year'], downcast='float')
                assert(all(hazard_events['Event Probability in Start Year'] >= 0))
            except:
                error_text = "MODEL PARAMETERS FILE ERROR: Event Probability in Start Year column could not be converted to non-negative float"
                logger.error(error_text)
                error_list.append(error_text)
            else:
                if cfg['roi_analysis_type'] == 'Regret':
                    try:
                        assert(all(hazard_events['Event Probability in Start Year'] == 1.0))
                    except:
                        error_text = "MODEL PARAMETERS FILE ERROR: Event Probability in Start Year column must be set to 1 for regret analysis"
                        logger.error(error_text)
                        error_list.append(error_text)

            hazards_list = hazard_events
            hazard = set(hazard_events['Hazard Event'].dropna().tolist()) 
            projgroup = set(projgroup_to_resil['Project Groups'].dropna().tolist())
            recovery = set(recovery['Recovery Stages'].dropna().tolist())
            resil = set(projgroup_to_resil['Resiliency Projects'].dropna().tolist())

            elasticity = pd.read_excel(model_params_file, sheet_name='Elasticities',
                                       converters={'Trip Loss Elasticities': float})
            elasticity = set(elasticity['Trip Loss Elasticities'].dropna().tolist())

            socio = pd.read_excel(model_params_file, sheet_name='EconomicScenarios',
                                  converters={'Economic Scenarios': str})     
            socio = set(socio['Economic Scenarios'].dropna().tolist())

    # ---------------------------------------------------------------------------------------------------
    # Exposure analysis files
    # For each hazard listed in Model_Parameters.xlsx:
    # 1) Is there a hazard CSV file
    # 2) Check that link_id, from_node_id, to_node_id, Value (or similar) exist; from_node_id, to_node_id must be int, Value must be float
    hazard_folder = os.path.join(input_folder, 'Hazards')
    hazard_file_list = []
    if os.path.isdir(hazard_folder):
        for filename in os.listdir(hazard_folder):
            f = os.path.join(hazard_folder, filename)

            # Check if it is a file
            if os.path.isfile(f):
                hazard_file_list.append(filename)

        if has_error_hazards or not os.path.exists(model_params_file):
            error_text = "EXPOSURE ANALYSIS FILE WARNING: Not validating exposure analysis files, errors with Model_Parameters.xlsx"
            logger.error(error_text)
            error_list.append(error_text)
        else:
            for index, row in hazards_list.iterrows():  # From Model_Parameters section
                h = str(row['Filename']) + '.csv'
                # CSV STEP 1: Check file exists
                if h not in hazard_file_list:
                    error_text = "EXPOSURE ANALYSIS FILE ERROR: No exposure analysis file is present for hazard {} listed in Model_Parameters.xlsx".format(row['Hazard Event'])
                    logger.error(error_text)
                    error_list.append(error_text)
                else:
                    # CSV STEP 2: Check file has necessary columns
                    try:
                        exposures = pd.read_csv(os.path.join(hazard_folder, h), usecols=['link_id', 'from_node_id', 'to_node_id', cfg['exposure_field']],
                                                converters={'link_id': str, 'from_node_id': str, 'to_node_id': str, cfg['exposure_field']: str})
                    except:
                        error_text = "EXPOSURE ANALYSIS FILE ERROR: File for hazard {} is missing required columns".format(row['Hazard Event'])
                        logger.error(error_text)
                        error_list.append(error_text)
                    else:
                        # Test from_node_id can be converted to int
                        try:
                            exposures['from_node_id'] = pd.to_numeric(exposures['from_node_id'], downcast='integer')
                        except:
                            error_text = "EXPOSURE ANALYSIS FILE ERROR: Column from_node_id could not be converted to int for hazard {}".format(row['Hazard Event'])
                            logger.error(error_text)
                            error_list.append(error_text)

                        # Test to_node_id can be converted to int
                        try:
                            exposures['to_node_id'] = pd.to_numeric(exposures['to_node_id'], downcast='integer')
                        except:
                            error_text = "EXPOSURE ANALYSIS FILE ERROR: Column to_node_id could not be converted to int for hazard {}".format(row['Hazard Event'])
                            logger.error(error_text)
                            error_list.append(error_text)

                        # Test cfg['exposure_field'] can be converted to float
                        try:
                            exposures[cfg['exposure_field']] = pd.to_numeric(exposures[cfg['exposure_field']], downcast='float')
                        except:
                            error_text = "EXPOSURE ANALYSIS FILE ERROR: Column specifying exposure level could not be converted to float for hazard {}".format(row['Hazard Event'])
                            logger.error(error_text)
                            error_list.append(error_text)
    else:
        error_text = "EXPOSURE ANALYSIS FOLDER ERROR: Hazards directory for exposure analysis files does not exist"
        logger.error(error_text)
        error_list.append(error_text)

    # ---------------------------------------------------------------------------------------------------
    # Network attribute files - link and node
    # 1) Is there a node CSV file
    # 2) Check that node_id, x_coord, y_coord, node_type exist; node_id must be int, x_coord, y_coord must be float
    # 3) Check that node_id has no duplicate values
    # For each socio and project group listed in Model_Parameters.xlsx:
    # 1) Is there a links CSV file
    # 2) Check that link_id, from_node_id, to_node_id, directed, length, facility_type, capacity, free_speed, lanes, allowed_uses, toll, travel_time exist;
    #    from_node_id, to_node_id, directed, lanes must be int, length, capacity, free_speed, toll, travel_time must be float
    # 3) Check that link_id has no duplicate values
    # 4) Check that directed is always 1, allowed_uses is always c
    # 5) If 'nocar' trip table matrix exists, check that toll_nocar, travel_time_nocar exist; both must be float
    networks_folder = os.path.join(input_folder, 'Networks')

    if os.path.isdir(networks_folder):

        node_file = os.path.join(networks_folder, 'node.csv')
        # These three variables are used at the end to report (if needed) that elements were excluded from the CSV report
        node_f_excl = False
        x_excl = False
        y_excl = False
        
        # CSV STEP 1: Check file exists
        if not os.path.exists(node_file):
            error_text = "NETWORK NODE FILE ERROR: Node input file could not be found"
            logger.error(error_text)
            error_list.append(error_text)
            node_f_excl = True
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
                    x_excl = True
                else:
                    # Compute summary statistics on x_coord values
                    x_coord_stats = summary_info_by_type(df = nodes, ind = 'node_type', val = 'x_coord', file = node_file, notes = "")
                    param_dfs_list.append(x_coord_stats)                       

                # Test y_coord can be converted to float
                try:
                    nodes['y_coord'] = pd.to_numeric(nodes['y_coord'], downcast='float')
                except:
                    error_text = "NETWORK NODE FILE ERROR: Column y_coord could not be converted to float"
                    logger.error(error_text)
                    error_list.append(error_text)
                    y_excl = True
                else:
                    # Compute summary statistics on y_coord values
                    y_coord_stats = summary_info_by_type(df = nodes, ind = 'node_type', val = 'y_coord', file = node_file, notes = "") 
                    param_dfs_list.append(y_coord_stats)   

        links_file_list = []
        for filename in os.listdir(networks_folder):
            if filename != 'node.csv':
                f = os.path.join(networks_folder, filename)

                # Check if it is a file
                if os.path.isfile(f):
                    links_file_list.append(filename)

        if has_error_model_params:
            error_text = "NETWORK LINK FILE WARNING: Not validating network link files, errors with Model_Parameters.xlsx"
            logger.error(error_text)
            error_list.append(error_text)
        else:
            for i in socio:
                for j in projgroup:
                    # CSV STEP 1: Check file exists
                    link_file = i + j + '.csv'
                    if link_file not in links_file_list:
                        error_text = "NETWORK LINK FILE ERROR: No network link file is present for socio {} and project group {} listed in Model_Parameters.xlsx".format(i, j)
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

                            # Test lanes can be converted to int and all values are positive integers (not negative, zero, or blank)
                            try:
                                links['lanes'] = pd.to_numeric(links['lanes'], downcast='integer')
                                assert(all(links['lanes'] > 0))
                            except:
                                error_text = "NETWORK LINK FILE ERROR: Column lanes has at least one value that is not a positive integer (or is blank) for socio {} and project group {}".format(i, j)
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

                            demand_folder = os.path.join(input_folder, 'AEMaster', 'matrices')
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

        for link_file in links_file_list:
            try:
                links = pd.read_csv(os.path.join(networks_folder, link_file),
                                    usecols=['facility_type', 'length', 'capacity', 'free_speed', 'toll', 'travel_time'],
                                    converters={'facility_type': str, 'length': float, 'capacity': float, 'free_speed': float, 'toll': float, 'travel_time': float})
            except:
                excluded_list.append(link_file)
            else:
                # Compute summary statistics
                df_length_name = f"length_stats_{link_file}"
                globals()[df_length_name] = summary_info_by_type(df = links, ind = 'facility_type', val = 'length', file = os.path.join(networks_folder, link_file), notes = "The units for length are miles.")
                param_dfs_list.append(globals()[df_length_name])

                df_capacity_name = f"capacity_stats_{link_file}"
                globals()[df_capacity_name] = summary_info_by_type(df = links, ind = 'facility_type', val = 'capacity', file = os.path.join(networks_folder, link_file), notes = "The units for capacity are vehicles per day per lane.")
                param_dfs_list.append(globals()[df_capacity_name])                            

                df_speed_name = f"speed_stats_{link_file}"
                globals()[df_speed_name] = summary_info_by_type(df = links, ind = 'facility_type', val = 'free_speed', file = os.path.join(networks_folder, link_file), notes = "The units for free speed are miles per hour.")
                param_dfs_list.append(globals()[df_speed_name])

                df_toll_name = f"toll_stats_{link_file}"
                globals()[df_toll_name] = summary_info_by_type(df = links, ind = 'facility_type', val = 'toll', file = os.path.join(networks_folder, link_file), notes = "The units for toll are cents.")
                param_dfs_list.append(globals()[df_toll_name])

                df_travel_time_name = f"time_stats_{link_file}"
                globals()[df_travel_time_name] = summary_info_by_type(df = links, ind = 'facility_type', val = 'travel_time', file = os.path.join(networks_folder, link_file), notes = "The units for travel time are minutes.")
                param_dfs_list.append(globals()[df_travel_time_name])                                         
    else:
        error_text = "NETWORK FOLDER ERROR: Networks directory for network attribute files does not exist"
        logger.error(error_text)
        error_list.append(error_text)

    # ---------------------------------------------------------------------------------------------------
    # Demand files
    # For each socio listed in Model_Parameters.xlsx:
    # 1) Is there a demand OMX file
    # 2) Check OMX file has 'matrix' square demand matrix and 'taz' mapping
    # 3) If 'nocar' trip table matrix, check that it is square
    demand_folder = os.path.join(input_folder, 'AEMaster', 'matrices')

    if os.path.isdir(demand_folder):
        demand_file_list = []
        for filename in os.listdir(demand_folder):
            f = os.path.join(demand_folder, filename)

            # Check if it is a file
            if os.path.isfile(f):
                demand_file_list.append(filename)

        if has_error_model_params:
            error_text = "DEMAND FILE WARNING: Not validating demand OMX files, errors with Model_Parameters.xlsx"
            logger.error(error_text)
            error_list.append(error_text)
        else:
            for i in socio:
                # OMX STEP 1: Check file exists
                demand_file = i + '_demand_summed.omx'
                if demand_file not in demand_file_list:
                    error_text = "DEMAND FILE ERROR: No demand OMX file is present for socio {} listed in Model_Parameters.xlsx".format(i)
                    logger.error(error_text)
                    error_list.append(error_text)
                else:
                    try:
                        omx_file = omx.open_file(os.path.join(demand_folder, demand_file))
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

    # ---------------------------------------------------------------------------------------------------
    # SQLite database
    # 1) Is project_database.sqlite present in the AEMaster directory
    # 2) Check list of tables matches expected list of tables
    AEMaster_folder = os.path.join(input_folder, 'AEMaster')
    network_db_file = os.path.join(AEMaster_folder, 'project_database.sqlite')

    if not os.path.exists(network_db_file):
        error_text = "SQLite DATABASE FILE ERROR: {} could not be found".format(network_db_file)
        logger.error(error_text)
        error_list.append(error_text)
    else:
        with sqlite3.connect(network_db_file) as db_con:
            cur = db_con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            all_tables = cur.fetchall()
            nodes_exists = ('nodes',) in all_tables
            links_exists = ('links',) in all_tables

        if not nodes_exists:
            error_text = "SQLite DATABASE FILE ERROR: `nodes` table could not be found in {}".format(network_db_file)
            logger.error(error_text)
            error_list.append(error_text)

        if not links_exists:
            error_text = "SQLite DATABASE FILE ERROR: `links` table could not be found in {}".format(network_db_file)
            logger.error(error_text)
            error_list.append(error_text)

    # ---------------------------------------------------------------------------------------------------
    # Base year core model runs file
    # 1) Is it present for the corresponding SP/RT outputs, Metamodel_scenario_SP_baseyear.csv OR Metamodel_scenario_RT_baseyear.csv
    # 2) Check that hazard, recovery, trips, miles, hours exist; recovery must be int, trips, miles, hours must be float
    baseyear_option = cfg['aeq_run_type']
    baseyear_files = []
    b_y = 'Metamodel_scenarios_' + baseyear_option + '_baseyear.csv'
    baseyear_files.append(os.path.join(input_folder, b_y))

    # CSV STEP 1: Check file exists
    any_baseyear_error = []
    for b_y in baseyear_files:
        any_baseyear_error.append(not os.path.exists(b_y))

    if all(any_baseyear_error):
        error_text = "BASE YEAR MODEL FILE ERROR: {} could not be found in {}".format(b_y, input_folder)
        logger.error(error_text)
        error_list.append(error_text)
    else:
        # CSV STEP 2: Check file has necessary columns
        # Read the first base year file available and verify columns
        try:
            baseyear = pd.read_csv(baseyear_files[0], usecols=['hazard', 'recovery', 'trips', 'miles', 'hours'],
                                   converters={'hazard': str, 'recovery': str, 'trips': str, 'miles': str, 'hours': str})
        except:
            error_text = "BASE YEAR MODEL FILE ERROR: Base year core model runs input file is missing required columns"
            logger.error(error_text)
            error_list.append(error_text)
        else:
            # Test recovery stages are nonnegative numbers
            try:
                recovery_num = pd.to_numeric(baseyear['recovery'], downcast='float')
                assert(all(recovery_num >= 0))
            except:
                error_text = "BASE YEAR MODEL FILE ERROR: Recovery stages are not all nonnegative numbers"
                logger.error(error_text)
                error_list.append(error_text)

            # Test trips can be converted to float
            try:
                baseyear['trips'] = pd.to_numeric(baseyear['trips'], downcast='float')
            except:
                error_text = "BASE YEAR MODEL FILE ERROR: Column trips could not be converted to float"
                logger.error(error_text)
                error_list.append(error_text)

            # Test miles can be converted to float
            try:
                baseyear['miles'] = pd.to_numeric(baseyear['miles'], downcast='float')
            except:
                error_text = "BASE YEAR MODEL FILE ERROR: Column miles could not be converted to float"
                logger.error(error_text)
                error_list.append(error_text)

            # Test hours can be converted to float
            try:
                baseyear['hours'] = pd.to_numeric(baseyear['hours'], downcast='float')
            except:
                error_text = "BASE YEAR MODEL FILE ERROR: Column hours could not be converted to float"
                logger.error(error_text)
                error_list.append(error_text)

            # Test hazard-recovery pairs can be found for every pair in Model_Parameters.xlsx
            try:
                hazard_b_y = set(baseyear['hazard'].dropna().tolist())
                recovery_b_y = set(baseyear['recovery'].dropna().tolist())
                product_m_p = set(list(product(hazard, recovery)))
                product_b_y = set(list(product(hazard_b_y, recovery_b_y)))
                assert(product_m_p <= product_b_y)
            except:
                error_text = "BASE YEAR MODEL FILE ERROR: Base year core model runs input file is missing at least one hazard-recovery combination"
                logger.error(error_text)
                error_list.append(error_text)

    # ---------------------------------------------------------------------------------------------------
    # Resilience projects files
    # 1) Are project_info.csv and project_table.csv files present
    # 2) Check that project_info.csv has columns Project ID, Project Name, Asset, Project Cost, Project Lifespan, Annual Maintenance Cost if exists, Redeployment Cost if exists; Project Cost, Annual Maintenance Cost, and Redeployment Cost should be converted to dollar
    # 3) Check that project_table.csv has columns link_id, Project ID, Category; Exposure Reduction must be float if exists
    resil_folder = os.path.join(input_folder, 'LookupTables')

    if os.path.isdir(resil_folder):
        # CSV STEP 1: Check file exists
        project_info_file = os.path.join(resil_folder, 'project_info.csv')
        if not os.path.exists(project_info_file):
            error_text = "RESILIENCE PROJECTS FILE ERROR: Project info input file could not be found"
            logger.error(error_text)
            error_list.append(error_text)
        else:
            # CSV STEP 2: Check file has necessary columns
            try:
                maintenance = cfg['maintenance']
                redeployment = cfg['redeployment']
                if maintenance and redeployment:
                    project_info = pd.read_csv(project_info_file, usecols=['Project ID', 'Project Name', 'Asset', 'Project Cost',
                                                                           'Project Lifespan', 'Annual Maintenance Cost', 'Redeployment Cost'],
                                               converters={'Project ID': str, 'Project Name': str, 'Asset': str, 'Project Cost': str,
                                                           'Project Lifespan': str, 'Annual Maintenance Cost': str, 'Redeployment Cost': str})
                elif maintenance:
                    project_info = pd.read_csv(project_info_file, usecols=['Project ID', 'Project Name', 'Asset', 'Project Cost',
                                                                           'Project Lifespan', 'Annual Maintenance Cost'],
                                               converters={'Project ID': str, 'Project Name': str, 'Asset': str, 'Project Cost': str,
                                                           'Project Lifespan': str, 'Annual Maintenance Cost': str})
                elif redeployment:
                    project_info = pd.read_csv(project_info_file, usecols=['Project ID', 'Project Name', 'Asset', 'Project Cost',
                                                                           'Project Lifespan', 'Redeployment Cost'],
                                               converters={'Project ID': str, 'Project Name': str, 'Asset': str, 'Project Cost': str,
                                                           'Project Lifespan': str, 'Redeployment Cost': str})
                else:
                    project_info = pd.read_csv(project_info_file, usecols=['Project ID', 'Project Name', 'Asset', 'Project Cost',
                                                                           'Project Lifespan'],
                                               converters={'Project ID': str, 'Project Name': str, 'Asset': str, 'Project Cost': str,
                                                           'Project Lifespan': str})
            except:
                error_text = "RESILIENCE PROJECTS FILE ERROR: Project info input file is missing required columns"
                logger.error(error_text)
                error_list.append(error_text)
            else:
                # Test Project Cost can be converted to dollar amount
                try:
                    project_cost = project_info['Project Cost'].replace('[\$,]', '', regex=True).replace('', '0.0').astype(float)
                except:
                    error_text = "RESILIENCE PROJECTS FILE ERROR: Column Project Cost could not be translated to dollar amount in project info input file"
                    logger.error(error_text)
                    error_list.append(error_text)
                else:
                    if cfg['roi_analysis_type'] == 'Breakeven':
                        try:
                            assert(all(project_cost == 0))
                        except:
                            error_text = "RESILIENCE PROJECTS FILE ERROR: For breakeven analysis, Project Cost should be set to zero in project info input file"
                            logger.error(error_text)
                            error_list.append(error_text)

                # Test Project Lifespan can be converted to int
                try:
                    project_info['Project Lifespan'] = pd.to_numeric(project_info['Project Lifespan'], downcast='integer')
                    assert(all(project_info['Project Lifespan'] >= 0))
                except:
                    error_text = "RESILIENCE PROJECTS FILE ERROR: Column Project Lifespan could not be converted to positive integers in project info input file"
                    logger.error(error_text)
                    error_list.append(error_text)

                # Test Annual Maintenance Cost can be converted to dollar amount
                if maintenance:
                    try:
                        project_cost = project_info['Annual Maintenance Cost'].replace('[\$,]', '', regex=True).replace('', '0.0').astype(float)
                    except:
                        error_text = "RESILIENCE PROJECTS FILE ERROR: Column Annual Maintenance Cost could not be translated to dollar amount in project info input file"
                        logger.error(error_text)
                        error_list.append(error_text)

                # Test Redeployment Cost can be converted to dollar amount
                if redeployment:
                    try:
                        project_cost = project_info['Redeployment Cost'].replace('[\$,]', '', regex=True).replace('', '0.0').astype(float)
                    except:
                        error_text = "RESILIENCE PROJECTS FILE ERROR: Column Redeployment Cost could not be translated to dollar amount in project info input file"
                        logger.error(error_text)
                        error_list.append(error_text)

                # Confirm resilience projects are a subset of those listed in this input file
                if not has_error_resil_projects:
                    try:
                        assert(resil <= set(project_info['Project ID'].dropna().tolist()))
                    except:
                        error_text = "RESILIENCE PROJECTS FILE ERROR: Missing resilience projects in project info input file"
                        logger.error(error_text)
                        error_list.append(error_text)

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

                # Confirm Category is either 'Highway', 'Bridge', or 'Transit' if using default repair tables
                if cfg['repair_cost_approach'] == 'Default' or cfg['repair_time_approach'] == 'Default':
                    try:
                        assert(all(project_table['Category'].isin(['Highway', 'Bridge', 'Transit'])))
                    except:
                        error_text = "RESILIENCE PROJECTS FILE ERROR: Category values in project table input file must be 'Highway', 'Bridge', or 'Transit' if using default repair tables"
                        logger.error(error_text)
                        error_list.append(error_text)

                # Confirm resilience projects are a subset of those listed in this project table file
                if not has_error_resil_projects:
                    try:
                        assert(resil <= set(project_table['Project ID'].dropna().tolist()))
                    except:
                        error_text = "RESILIENCE PROJECTS TABLE FILE ERROR: Missing resilience projects in project table input file"
                        logger.error(error_text)
                        error_list.append(error_text)
    else:
        error_text = "RESILIENCE PROJECTS FOLDER ERROR: LookupTables directory for resilience projects files does not exist"
        logger.error(error_text)
        error_list.append(error_text)

    # ---------------------------------------------------------------------------------------------------
    # LAST STEPS

    # Produce a CSV output to help user review inputs to ensure they are reasonable
    if len(param_dfs_list) > 0:
        run_id = cfg['run_id']
        param_stats_df = pd.concat(param_dfs_list, ignore_index=True)
        csv_filepath = os.path.join(output_folder, 'logs', 'input_validation_parameter_stats_{}_{}.csv'.format(run_id, datetime.datetime.now().strftime("%Y_%m_%d_%H-%M-%S")))
        param_stats_df.to_csv(csv_filepath, index = False) 
        # Tell the user about the CSV file that they can use to check whether values are reasonable
        logger.info("A file with summary statistics on certain fields is available at: " + os.path.join(output_folder, 'logs', 'input_validation_parameter_stats_{}_{}.csv'.format(run_id, datetime.datetime.now().strftime("%Y_%m_%d_%H-%M-%S"))))
        logger.info("Open it to check whether values are reasonable and match what was entered.")
    if len(excluded_list) > 0:
        warning_text = "Note: There is a problem with one or more link files: {}. As a result, summary statistics will not appear in the CSV file referenced above for the file(s). Consult prior messages in log file to understand the problem(s).".format(excluded_list)
        logger.warning(warning_text)
    if node_f_excl:
        warning_text = "Note: The node.csv file could not be found so summary statistics will not appear in the CSV file referenced above for x_coord and y_coord (which would have come from the node.csv file)."
        logger.warning(warning_text)
    if x_excl:
        warning_text = "Note: The x_coord column in the node.csv file could not be converted to float so summary statistics will not appear in the CSV file referenced above."
        logger.warning(warning_text)
    if y_excl:
        warning_text = "Note: The y_coord column in the node.csv file could not be converted to float so summary statistics will not appear in the CSV file referenced above."
        logger.warning(warning_text)

    # If any check failed, raise exception
    if len(error_list) > 0:
        logger.error(("Exiting script with {} breaking errors found! See logger.error outputs in log file for details. Consult the Run Checklist and User Guide to fix.".format(len(error_list))))
        raise Exception("Exiting script with {} breaking errors found! See logger.error outputs in log file for details. Consult the Run Checklist and User Guide to fix.".format(len(error_list)))
    else:
        # Inform the user that the check passed
        logger.info("All input validation checks passed successfully! No errors found.")

    return


# ---------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    main()
