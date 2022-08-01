#!/usr/bin/env python
# coding: utf-8


# ---------------------------------------------------------------------------------------------------
# Name: rdr_CompileAE
#
# Consolidates outputs from AequilibraE runs to pass to regression module.
#
# ---------------------------------------------------------------------------------------------------
import os
import pandas as pd


def main(input_folder, output_folder, cfg, logger, base_year):
    logger.info("Start: AequilibraE compile module")

    # to avoid issues with a set of runs going past midnight, using cfg['run_id'] in folder name instead of date
    # make list of completed runs
    if base_year is True:
        aeq_runs_folder = os.path.join(output_folder, 'aeq_runs_base_year', 'disrupt', str(cfg['run_id']))
    else:
        aeq_runs_folder = os.path.join(output_folder, 'aeq_runs', 'disrupt', str(cfg['run_id']))
    if not os.path.exists(aeq_runs_folder):
        logger.error("AEQUILIBRAE FOLDER ERROR: {} could not be found".format(aeq_runs_folder))
        raise Exception("AEQUILIBRAE FOLDER ERROR: {} could not be found".format(aeq_runs_folder))
    completed_runs = os.listdir(aeq_runs_folder)
    if len(completed_runs) == 0:
        logger.error("MISSING AEQUILIBRAE RUNS ERROR: {} contains no AequilibraE runs".format(aeq_runs_folder))
        raise Exception("MISSING AEQUILIBRAE RUNS ERROR: {} contains no AequilibraE runs".format(aeq_runs_folder))

    # make empty container to hold compiled results
    compiled_results = []

    # step through each completed run, read in NetSkim.csv, and append results
    for run in completed_runs:
        try:
            run_result = pd.read_csv(os.path.join(aeq_runs_folder, run, 'NetSkim.csv'),
                                     converters={'Type': str, 'SP/RT': str, 'socio': str, 'projgroup': str,
                                                 'resil': str, 'elasticity': float, 'hazard': str, 'recovery': str,
                                                 'Scenario': str})
            compiled_results.append(run_result)
        except:
            logger.warning('Error reading run ' + run + ' while compiling results')

    if len(compiled_results) == 0:
        logger.error("MISSING AEQUILIBRAE RUNS ERROR: {} contains no AequilibraE runs".format(aeq_runs_folder))
        raise Exception("MISSING AEQUILIBRAE RUNS ERROR: {} contains no AequilibraE runs".format(aeq_runs_folder))
    else:
        compiled_results = pd.concat(compiled_results)

    if base_year is True:
        # write out the compiled results as a csv in the input folder
        compiled_results.to_csv(os.path.join(input_folder, 'Metamodel_scenarios_baseyear.csv'), index=False)
    else:
        # write out the compiled results as an xlsx in the output folder
        compiled_results.to_excel(os.path.join(output_folder, 'AequilibraE_Runs_Compiled_' + str(cfg['run_id']) + '.xlsx'),
                                  index=False)

    logger.info("Finished: AequilibraE compile module")
