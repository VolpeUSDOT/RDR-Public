#!/usr/bin/env python
# coding: utf-8


# ---------------------------------------------------------------------------------------------------
# Name: rdr_LHS
#
# Defines AequilibraE runs needed to fill in around TDM to parameterize regression model.
#
# ---------------------------------------------------------------------------------------------------
import os
import pandas as pd
import shutil
import subprocess
from itertools import product
from rdr_supporting import log_subprocess_output, log_subprocess_error


def main(input_folder, output_folder, cfg, logger):
    logger.info("Start: latin hypercube module")

    # Build out the scenario space for input into LHS algorithm
    model_params_file = os.path.join(input_folder, 'Model_Parameters.xlsx')
    full_combos_file = os.path.join(output_folder, 'full_combos_' + str(cfg['run_id']) + '.csv')

    if not os.path.exists(model_params_file):
        logger.error("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
        raise Exception("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))

    # Check input files (demand, exposure, network) are sufficient for the scenario space
    is_covered = check_model_params_coverage(model_params_file, input_folder, logger)
    if is_covered == 0:
        logger.error(("INSUFFICIENT INPUT DATA ERROR: missing input files for " +
                      "scenario space defined by {}".format(model_params_file)))
        raise Exception(("INSUFFICIENT INPUT DATA ERROR: missing input files for " +
                         "scenario space defined by {}".format(model_params_file)))

    model_params = pd.read_excel(model_params_file, sheet_name='UncertaintyParameters',
                                 converters={'Hazard Events': str, 'Recovery Stages': str,
                                             'Economic Scenarios': str, 'Trip Loss Elasticities': float,
                                             'Project Groups': str})
    projgroup_to_resil = pd.read_excel(model_params_file, sheet_name='ProjectGroups',
                                       converters={'Project Groups': str, 'Resiliency Projects': str})
    # Ensure baseline scenario of no resilience investment is included
    if projgroup_to_resil['Resiliency Projects'].str.contains('no').any():
        logger.warning("Resilience projects labeled 'no' are assumed to indicate no resilience investment.")
    projgroup_to_resil_copy = projgroup_to_resil.copy(deep=True)
    projgroup_to_resil_copy.loc[:, ['Resiliency Projects']] = 'no'
    projgroup_to_resil = pd.concat([projgroup_to_resil, projgroup_to_resil_copy], ignore_index=True)
    projgroup_to_resil = projgroup_to_resil.loc[:, ['Project Groups',
                                                    'Resiliency Projects']].drop_duplicates(ignore_index=True)

    socio = set(model_params['Economic Scenarios'].dropna().tolist())
    logger.config("List of economic scenarios: \t{}".format(', '.join(str(e) for e in socio)))
    projgroup = set(model_params['Project Groups'].dropna().tolist())
    logger.config("List of project groups: \t{}".format(', '.join(str(e) for e in projgroup)))
    elasticity = set(model_params['Trip Loss Elasticities'].dropna().tolist())
    logger.config("List of elasticities: \t{}".format(', '.join(str(e) for e in elasticity)))
    hazard = set(model_params['Hazard Events'].dropna().tolist())
    logger.config("List of hazards: \t{}".format(', '.join(str(e) for e in hazard)))
    recovery = set(model_params['Recovery Stages'].dropna().tolist())
    logger.config("List of recovery stages: \t{}".format(', '.join(str(e) for e in recovery)))

    resil = set(projgroup_to_resil['Resiliency Projects'].dropna().tolist())
    logger.config("List of resilience projects: \t{}".format(', '.join(str(e) for e in resil)))

    combo_list = list(product(socio, projgroup, elasticity, hazard, recovery))
    combo_list.sort()

    product1 = pd.DataFrame(combo_list,
                            columns=['socio', 'projgroup', 'elasticity', 'hazard', 'recovery'])
    full_combos = pd.merge(product1, projgroup_to_resil, how='left',
                           left_on='projgroup', right_on='Project Groups', indicator=True)
    logger.debug(("Number of project groups not matched to resilience " +
                  "projects: {}".format(sum(full_combos['_merge'] == 'left_only'))))
    if sum(full_combos['_merge'] == 'left_only') > 0:
        logger.warning(("TABLE JOIN WARNING: Some project groups in the scenario space definition were not " +
                        "found in ProjectGroups tab of Model_Parameters.xlsx and will be excluded in analysis."))
    full_combos = full_combos.loc[full_combos['_merge'] == 'both', :]
    full_combos.drop(labels=['Project Groups', '_merge'], axis=1, inplace=True)
    full_combos.rename({'Resiliency Projects': 'resil'}, axis='columns', inplace=True)
    logger.debug("Size of full scenario space: {}".format(full_combos.shape))

    with open(full_combos_file, "w", newline='') as f:
        full_combos.to_csv(f, index=False)
        logger.result("Full scenario space written to {}".format(full_combos_file))

    """
    Execute rdr_LHS.R, which reads from the Model_Parameters file and creates the AequilibraE design.

    Note! A number of R package dependencies will be installed by rdr_Rutil.R.
    """

    # Validate that rdr_LHS.R is present in the current directory
    if not os.path.exists('rdr_LHS.R'):
        logger.error("R CODE FILE ERROR: rdr_LHS.R could not be found in directory {}".format(os.getcwd()))
        raise Exception("R CODE FILE ERROR: rdr_LHS.R could not be found in directory {}".format(os.getcwd()))

    # Validate that Rscript.exe is callable
    if shutil.which('Rscript.exe') is None:
        logger.error("R EXECUTABLE ERROR: Rscript.exe could not be found")
        raise Exception("R EXECUTABLE ERROR: Rscript.exe could not be found")

    # Pass arguments to R as strings, not int or other

    # Target number for initial LHS design
    lhs_sample_target = str(cfg['lhs_sample_target'])

    # Indicator for whether this is for additional runs
    do_additional_runs = str(cfg['do_additional_runs'])

    # If additional runs, how many
    # Set to '0' if 'do_additional_runs' is 'False', regardless of value in 'lhs_sample_add_target'
    if do_additional_runs == 'True':
        lhs_sample_additional_target = str(cfg['lhs_sample_additional_target'])
    else:
        lhs_sample_additional_target = '0'
        if cfg['lhs_sample_additional_target'] != 0:
            logger.warning("Parameter 'do_additional_runs' is set to False, yet additional runs have been specified in "
                           "'lhs_sample_additional_target'. No additional runs will be done. Review the config file.")

    # Metamodel type to run
    # Final LHS design depends on what type of model is run
    metamodel_type = str(cfg['metamodel_type'])

    # Check to see if the random number generator seed has been specified
    # If so, pass the seed as an argument to R process
    if cfg['seed'] is not None:
        R_process = subprocess.Popen(['Rscript.exe', 'rdr_LHS.R', input_folder, output_folder, cfg['run_id'],
                                     lhs_sample_target, lhs_sample_additional_target,
                                     metamodel_type, str(cfg['seed'])],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        R_process = subprocess.Popen(['Rscript.exe', 'rdr_LHS.R', input_folder, output_folder, cfg['run_id'],
                                     lhs_sample_target, lhs_sample_additional_target,
                                     metamodel_type],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    log_subprocess_output(R_process.stdout, logger)
    log_subprocess_error(R_process.stderr, logger)
    if R_process.stderr.readline() != b'':
        logger.error("LHS R CODE ERROR: rdr_LHS.R encountered an error")
        raise Exception("LHS R CODE ERROR: rdr_LHS.R encountered an error")

    logger.info("Finished: latin hypercube module")


# ==============================================================================


def check_model_params_coverage(model_params_file, input_folder, logger):
    logger.info("Start: check_model_params_coverage")
    is_covered = 1

    # If params_file is "Model_Parameters.xlsx" then sheet_name = 'UncertaintyParameters'
    model_params = pd.read_excel(model_params_file, sheet_name='UncertaintyParameters',
                                 usecols=['Hazard Events', 'Economic Scenarios', 'Project Groups'],
                                 converters={'Hazard Events': str, 'Economic Scenarios': str, 'Project Groups': str})
    hazard_events = pd.read_excel(model_params_file, sheet_name='Hazards',
                                  usecols=['Hazard Event', 'Filename'],
                                  converters={'Hazard Event': str, 'Filename': str})

    # Read in columns 'Hazard Events', 'Economic Scenarios', 'Project Groups'
    # Do not need to check resilience project coverage; if no links are listed in project_table.csv then no effect
    hazard = set(model_params['Hazard Events'].dropna().tolist())
    socio = set(model_params['Economic Scenarios'].dropna().tolist())
    projgroup = set(model_params['Project Groups'].dropna().tolist())

    # Check demand OMX files, exposure CSV files, network CSV files
    for i in socio:
        filename = os.path.join(input_folder, 'AEMaster', 'matrices', i + '_demand_summed.omx')
        if not os.path.exists(filename):
            is_covered = 0
            logger.error("Missing input file {}".format(filename))

    hazards_list = pd.merge(pd.DataFrame(hazard, columns=['Hazard Event']),
                            hazard_events, how='left', on='Hazard Event')
    for index, row in hazards_list.iterrows():
        filename = os.path.join(input_folder, 'Hazards', str(row['Filename']) + '.csv')
        if not os.path.exists(filename):
            is_covered = 0
            logger.error("Missing input file {}".format(filename))

    for i in socio:
        for j in projgroup:
            filename = os.path.join(input_folder, 'Networks', i + j + '.csv')
            if not os.path.exists(filename):
                is_covered = 0
                logger.error("Missing input file {}".format(filename))

    logger.info("Finished: check_model_params_coverage")
    return is_covered
