#!/usr/bin/env python
# coding: utf-8


# ---------------------------------------------------------------------------------------------------
# Name: rdr_RunAE
#
# Wrapper for running AequilibraE for scenarios designated by Latin hypercube.
#
# ---------------------------------------------------------------------------------------------------
import os
import copy
import pandas as pd
import openmatrix as omx
import sqlite3
import rdr_AESingleRun


def main(input_folder, output_folder, cfg, logger):
    logger.info("Start: AequilibraE run module")

    target = cfg['lhs_sample_target']

    # read in table output by Latin hypercube module
    lhs_file = os.path.join(output_folder, 'AequilibraE_LHS_Design_' + str(cfg['run_id']) + '_' +
                            str(target) + '.csv')

    if not os.path.exists(lhs_file):
        logger.error("LHS OUTPUT FILE ERROR: {} could not be found".format(lhs_file))
        raise Exception("LHS OUTPUT FILE ERROR: {} could not be found".format(lhs_file))

    lhs_runs = pd.read_csv(lhs_file, converters={'socio': str, 'projgroup': str, 'elasticity': float, 'hazard': str,
                                                 'recovery': str, 'resil': str, 'ID': str, 'LHS_ID': str})

    # set up AEMaster SQLite database with node information
    logger.info("importing node input file into SQLite database")
    node_file = os.path.join(input_folder, 'Networks', 'node.csv')
    network_db = os.path.join(input_folder, 'AEMaster', 'project_database.sqlite')
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
            # use to_sql to import df_node as table named GMNS_node
            # NOTE for to_sql: "Legacy support is provided for sqlite3.Connection objects."
            df_node.to_sql('GMNS_node', db_con, if_exists='replace', index=False)
            db_cur = db_con.cursor()

            # delete existing nodes table
            sql1 = "delete from nodes;"
            db_cur.execute(sql1)
            # insert node data into nodes table
            sql2 = """insert into nodes (ogc_fid, node_id, x, y, is_centroid)
                    select node_id, node_id, x_coord, y_coord, case node_type when 'centroid' then 1 else 0 end
                    from GMNS_node
                    order by node_id asc;"""
            db_cur.execute(sql2)
            logger.info("completed importing node input file into SQLite database")

    # log a warning if AequilibraE folders for run ID already exists
    base_runs_folder = os.path.join(output_folder, 'aeq_runs', 'base', str(cfg['run_id']))
    disrupt_runs_folder = os.path.join(output_folder, 'aeq_runs', 'disrupt', str(cfg['run_id']))
    if os.path.exists(base_runs_folder):
        logger.warning("Base AequilibraE runs folder for {} already exists, appending runs".format(cfg['run_id']))
    if os.path.exists(disrupt_runs_folder):
        logger.warning("Disrupt AequilibraE runs folder for {} already exists, appending runs".format(cfg['run_id']))

    # call run_AESingleRun method in rdr_AESingleRun.py for each row of LHS table indicated as selected sample run
    for index, row in lhs_runs.iterrows():
        if row['LHS_ID'] != 'NA':
            run_params = copy.deepcopy(row)
            run_params['run_minieq'] = cfg['run_minieq']
            run_params['matrix_name'] = 'matrix'  # always run AequilibraE for the default 'matrix'

            # determining whether run has already been done takes place within run_AESingleRun method
            rdr_AESingleRun.run_AESingleRun(run_params, input_folder, output_folder, cfg, logger)

            # run AequilibraE a second time if a 'nocar' trip table exists
            mtx_fldr = 'matrices'
            demand_file = os.path.join(input_folder, 'AEMaster', mtx_fldr, run_params['socio'] + '_demand_summed.omx')
            if not os.path.exists(demand_file):
                logger.error("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
                raise Exception("DEMAND OMX FILE ERROR: {} could not be found".format(demand_file))
            f = omx.open_file(demand_file)
            if 'nocar' in f.list_matrices():
                f.close()
                run_params['matrix_name'] = 'nocar'
                
                # determining whether run has already been done takes place within run_AESingleRun method
                rdr_AESingleRun.run_AESingleRun(run_params, input_folder, output_folder, cfg, logger)
            else:
                f.close()

    logger.info("Finished: AequilibraE run module")
