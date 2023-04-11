# Imports
import sys
import os
import argparse
import sqlite3
import pandas as pd
import openmatrix as omx
import subprocess
from itertools import product

# Import code from equity_config_reader.py, for read_equity_config_file method
import equity_config_reader

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'metamodel_py'))
import rdr_AESingleRun
import rdr_setup
import rdr_supporting

VERSION_NUMBER = "2023.1"
VERSION_DATE = "04/10/2023"
# ---------------------------------------------------------------------------------------------------
# The following code executes two core model runs to measure TAZ-to-TAZ trip metrics (e.g., skims) for a baseline "no action" scenario and a resilience project scenario for a particular hazard, socioeconomic future, and elasticity
# Users can use this tool to analyze the impact of a specific resilience project on trips taken between TAZs in the user's network, as identified by a categorical TAZ-level equity metric
# ---------------------------------------------------------------------------------------------------

def main():

    # ---------------------------------------------------------------------------------------------------
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
    category_filename = equity_cfg['output_name']

    # Set up logging and report run start time
    # ----------------------------------------------------------------------------------------------
    logger = rdr_supporting.create_loggers(output_dir, 'TAZ_metrics', equity_cfg)

    logger.info("=========================================================================")
    logger.info("=============== GENERATING MODEL RUNS FOR EQUITY ========================")
    logger.info("=========================================================================")

    logger.info("Reading in RDR config file")
    cfg = rdr_setup.read_config_file(rdr_cfg_path)

    # The helper tool requires AequilibraE inputs from the main RDR input directory
    # Logs and the scenarios' core model outputs are stored in the output directory output_dir
    input_dir = cfg['input_dir']

    logger.info("Checking required inputs for equity metrics run")

    # Look to see if the equity overlay data exists
    if not os.path.exists(os.path.join(output_dir, category_filename + '.csv')):
        logger.error('{}.csv not found in {}. Please run the equity overlay helper tool first.'.format(category_filename, output_dir))
        raise Exception("EQUITY CATEGORY FILE ERROR: {} could not be found".format(os.path.join(output_dir, category_filename + '.csv')))

    logger.info("Starting equity metrics run...")

    # ---------------------------------------------------------------------------------------------------
    # SETUP SQLITE nodes data
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
    run_params['run_minieq'] = equity_cfg['run_minieq']  # always 1 for equity analysis
    run_params['matrix_name'] = 'matrix'  # always run AequilibraE for the default 'matrix'

    # Method rdr_AESingleRun.run_AESingleRun runs both 'SP' and 'RT'; equity notebook uses config file parameter to pull correct skims from outputs
    rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)
    # For future development: Run AequilibraE a second time if a 'nocar' trip table exists
    # mtx_fldr = 'matrices'
    # demand_file = os.path.join(input_dir, 'AEMaster', mtx_fldr, run_params['socio'] + '_demand_summed.omx')
    # if not os.path.exists(demand_file):
    #     logger.error("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
    #     raise Exception("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
    # f = omx.open_file(demand_file)
    # if 'nocar' in f.list_matrices():
    #     f.close()
    #     run_params['matrix_name'] = 'nocar'
        
    #     rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)
    # else:
    #     f.close()

    logger.info("Finished running AequilibraE for baseline 'no action' scenario")

    # Resilience project core model run
    logger.info("Running AequilibraE for the resilience project scenario")
    run_params['resil'] = equity_cfg['resil']

    # Method rdr_AESingleRun.run_AESingleRun runs both 'SP' and 'RT'; equity notebook uses config file parameter to pull correct skims from outputs
    rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)
    # For future development: Run AequilibraE a second time if a 'nocar' trip table exists
    # mtx_fldr = 'matrices'
    # demand_file = os.path.join(input_dir, 'AEMaster', mtx_fldr, run_params['socio'] + '_demand_summed.omx')
    # if not os.path.exists(demand_file):
    #     logger.error("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
    #     raise Exception("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
    # f = omx.open_file(demand_file)
    # if 'nocar' in f.list_matrices():
    #     f.close()
    #     run_params['matrix_name'] = 'nocar'
        
    #     rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)
    # else:
    #     f.close()

    logger.info("Finished running AequilibraE for resilience project scenario")

    logger.info("Finished equity metrics run")


# ---------------------------------------------------------------------------------------------------
def run_notebook():
    
    if not os.path.exists(sys.argv[1]):
        print("ERROR: equity config file {} can't be found!".format(sys.argv[1]))
        sys.exit()

    equity_cfg = equity_config_reader.read_equity_config_file(sys.argv[1])

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

    logger = rdr_supporting.create_loggers(output_dir, 'TAZ_metrics_notebook', equity_cfg)

    if not os.path.exists(rdr_cfg_path):
        logger.error("ERROR: RDR config file {} can't be found!".format(rdr_cfg_path))
        sys.exit()

    # Values from RDR config file
    cfg = rdr_setup.read_config_file(rdr_cfg_path)
    RDR_run_id = cfg['run_id']

    notebook = os.path.join(os.getcwd(),'MetricsByTAZ.ipynb')
    if not os.path.exists(notebook):
        logger.info("The 'MetricsByTAZ.ipynb' notebook could not be found in {}.".format(os.getcwd()))
        sys.exit()

    # Check that the equity data file specified in the equity config exists
    if not os.path.exists(os.path.join(output_dir, category_filename + '.csv')):
        logger.error('{}.csv not found in {}. Please run the equity_overlay first or directly provide your own equity data file and specify the filename for it as output_name in the equity_metrics.config file.'.format(category_filename, output_dir))
        sys.exit()

    # Check that the equity data are numeric
    taz_equity = pd.read_csv(os.path.join(output_dir, category_filename + '.csv'),
                             usecols=['TAZ', category_name])
    if taz_equity[category_name].dtype == 'O':
        logger.error("Some of the data in {} are not numeric. The equity data must be binary or ordinal for the current version of this tool.".format(os.path.join(output_dir, category_filename + '.csv')))
        sys.exit()
    
    # Check that there are not too many unique values in the equity data
    if taz_equity[category_name].nunique() > 20:
        logger.warning("This tool is designed to handle equity data that are ordinal, with a small number of possible values. It is not designed to handle continous variables with many possible values. There are more than 20 unique values in the {} column of the {} file. For best results, pre-process your equity data by establishing bins and grouping by bin to result in fewer possible values.".format(category_name, category_filename + '.csv'))
        proceed = input('Per the above warning, this may not render well. Do you wish to proceed anyway? Type n to cancel (or any other key to proceed) followed by the enter key.')
        if proceed.lower() in ["n", "no"]:
            sys.exit()
    
    # Check that AequilibraE parameters that the user entered map to a file path associated with a corresponding RDR run
    # Location of the OMX files for "base" and for "disruption with resilience investment"
    omx_file_path = os.path.join(output_dir, "aeq_runs", "disrupt", RDR_run_id,
                                 socio + projgroup + '_' + resil + '_' + elasname + '_' + hazard + '_' + recovery, "matrix", "matrices")
    if not os.path.exists(omx_file_path):
        logger.error('The OMX folder path {} could not be found.'.format(omx_file_path))
        sys.exit()    
    # Location of the OMX files for "disruption WITHOUT resilience investment"
    omx_file_path_noresil = os.path.join(output_dir, "aeq_runs", "disrupt", RDR_run_id,
                                         socio + projgroup + '_' + baseline + '_' + elasname + '_' + hazard + '_' + recovery, "matrix", "matrices")
    if not os.path.exists(omx_file_path_noresil):
        logger.error('The OMX folder path {} could not be found.'.format(omx_file_path_noresil))
        sys.exit()    

    logger.info("=========================================================================")
    logger.info("=================== RUNNING TAZ REPORT NOTEBOOK =========================")
    logger.info("=========================================================================")

    # Notify user if a prior file will be overwritten
    existingFile = os.path.join(output_dir, 'MetricsByTAZ_' + run_id + '.html')
    if os.path.exists(existingFile):
        logger.warning("An existing file of the same name will be overwritten. A new MetricsByTAZ_{}.html file will be created in {}.".format(run_id, output_dir))

    # Create a temporary file to store the equity configuration file path so that the notebook can access it
    with open('temp.txt', 'w') as f:
        f.write(sys.argv[1])

    # Run the notebook
    subprocess.call(['jupyter-nbconvert',
                     '--execute',
                     '--to', 'html',
                     '--output-dir=' + output_dir,
                     '--no-input',
                     '--output', 'MetricsByTAZ_' + run_id + '.html',
                     "--ExecutePreprocessor.kernel_name='python3'",
                     'MetricsByTAZ.ipynb'])

    logger.info("MetricsByTAZ_{}.html created in {}".format(run_id, output_dir))

    # Delete temporary file
    os.remove('temp.txt')


# ---------------------------------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
    run_notebook()
