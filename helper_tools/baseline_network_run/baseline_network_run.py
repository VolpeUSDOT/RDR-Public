# Imports
import sys
import os
import argparse
import pandas as pd
import openmatrix as omx
import sqlite3
from itertools import product

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'metamodel_py'))
import rdr_AESingleRun
import rdr_setup
import rdr_supporting

VERSION_NUMBER = "2024.2.1"
VERSION_DATE = "2/3/2025"
# ---------------------------------------------------------------------------------------------------
# The following code generates AequilibraE outputs for a baseline scenario configuration
# with no hazard disruption and no resilience project improvements. Users can run this helper tool
# to validate the core model against an existing TDM run
# ---------------------------------------------------------------------------------------------------


def main():

    # PARSE ARGS
    # ----------------------------------------------------------------------------------------------

    program_description = 'Resilience Disaster Recovery Baseline Network Run Helper Tool: ' \
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
    error_list, cfg = rdr_setup.read_config_file(args.config_file, 'config')

    # Core model input files are put in the scenario's input dir
    input_dir = cfg['input_dir']

    # Logs and the scenario's outputs are put in the scenario's output dir
    output_dir = cfg['output_dir']

    # Set up logging
    logger = rdr_supporting.create_loggers(output_dir, 'baseline_run', cfg)
    if len(error_list) > 0:
        logger.error('\n'.join(error_list))
        raise Exception('{} errors found in config and/or setup file(s). Check log file in {} for list of errors.'.format(len(error_list)), output_dir)

    logger.info("Starting baseline network run...")

    # ---------------------------------------------------------------------------------------------------
    # MAIN

    # ---------------------------------------------------------------------------------------------------
    # SETUP SQLITE nodes data
    setup_sql_nodes(input_dir, logger)

    # ---------------------------------------------------------------------------------------------------
    # AEQ SINGLE RUNS
    # Creating dictionary for settings for Aequilibrae
    run_params = {}
    run_params['socio'] = 'baseline_run'  # always baseline_run for baseline network runs
    run_params['projgroup'] = ''  # always empty string (not used) for baseline network runs
    run_params['resil'] = 'no'  # always no for baseline network runs
    run_params['elasticity'] = -1  # always -1 for baseline network runs
    run_params['hazard'] = ''  # always empty string (not used) for baseline network runs
    run_params['recovery'] = ''  # always empty string (not used) for baseline network runs
    run_params['run_minieq'] = cfg['run_minieq']  # possibilities: 1 or 0
    run_params['matrix_name'] = 'matrix'  # always run AequilibraE for the default 'matrix'

    rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)

    # run AequilibraE a second time if a 'nocar' trip table exists
    mtx_fldr = 'matrices'
    demand_file = os.path.join(input_dir, 'AEMaster', mtx_fldr, run_params['socio'] + '_demand_summed.omx')
    if not os.path.exists(demand_file):
        logger.error("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
        raise Exception("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
    f = omx.open_file(demand_file)
    if 'nocar' in f.list_matrices():
        f.close()
        run_params['matrix_name'] = 'nocar'

        rdr_AESingleRun.run_AESingleRun(run_params, input_dir, output_dir, cfg, logger)
    else:
        f.close()

    logger.info("Finished baseline network run")


# ---------------------------------------------------------------------------------------------------
def setup_sql_nodes(input_dir, logger):
    # Aequilibrae requires a SQLite database to be setup first--this code is copied from rdr_RunAE.py
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


# ---------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()

