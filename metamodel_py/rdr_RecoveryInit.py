#!/usr/bin/env python
# coding: utf-8


# ---------------------------------------------------------------------------------------------------
# Name: rdr_RecoveryInit
#
# Purpose: Creates uncertainty scenarios from user inputs.
# Defines hazard duration cases and calculates repair costs/times.
#
# ---------------------------------------------------------------------------------------------------
import os
import copy
import numpy as np
import pandas as pd
import pandasql
from itertools import product


def main(input_folder, output_folder, cfg, logger):
    logger.info("Start: recovery initialization module")

    user_input_file = os.path.join(input_folder, 'UserInputs.xlsx')
    if not os.path.exists(user_input_file):
        logger.error("USER INPUTS FILE ERROR: {} could not be found".format(user_input_file))
        raise Exception("USER INPUTS FILE ERROR: {} could not be found".format(user_input_file))
    model_params_file = os.path.join(input_folder, 'Model_Parameters.xlsx')
    if not os.path.exists(model_params_file):
        logger.error("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
        raise Exception("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))

    # check input files (exposure, network) are sufficient for the scenario space
    is_covered = check_user_inputs_coverage(user_input_file, model_params_file, input_folder, logger)
    if is_covered == 0:
        logger.error(("INSUFFICIENT INPUT DATA ERROR: missing input files for " +
                      "scenario space defined by {}".format(user_input_file)))
        raise Exception(("INSUFFICIENT INPUT DATA ERROR: missing input files for " +
                         "scenario space defined by {}".format(user_input_file)))

    project_table = os.path.join(input_folder, 'LookupTables', 'project_table.csv')
    if not os.path.exists(project_table):
        logger.error("RESILIENCY PROJECTS FILE ERROR: {} could not be found".format(project_table))
        raise Exception("RESILIENCY PROJECTS FILE ERROR: {} could not be found".format(project_table))

    networks_folder = os.path.join(input_folder, 'Networks')
    exposures_folder = os.path.join(input_folder, 'Hazards')

    logger.config("Using project file: {}".format(project_table))
    logger.config("Using network files in folder: {}".format(networks_folder))
    logger.config("Using exposure files in folder: {}".format(exposures_folder))

    logger.info("building list of uncertainty scenarios")

    # uncertainty scenarios file is built from user inputs
    uncertainty_scenarios_file = os.path.join(output_folder, 'uncertainty_scenarios_' + str(cfg['run_id']) + '.csv')

    # uncertainty_scenarios_file built from (1) set of hazard events to analyze, (2) set of economic scenarios,
    # (3) set of trip loss elasticities, (4) set of resilience projects, (5) set of event frequency factors,
    # (6) set of project groups associated with resilience projects,
    # (7) set of assets to analyze (superset of (4)), (8) user parameters around hazard duration uncertainty
    user_inputs = pd.read_excel(user_input_file, sheet_name='UserInputs',
                                converters={'Hazard Events': str, 'Economic Scenarios': str,
                                            'Trip Loss Elasticities': float, 'Resiliency Projects': str,
                                            'Event Frequency Factors': float})
    projgroup_to_resil = pd.read_excel(model_params_file, sheet_name='ProjectGroups',
                                       converters={'Project Groups': str, 'Resiliency Projects': str})
    # ensure baseline scenario of no resilience investment is included
    projgroup_to_resil_copy = projgroup_to_resil.copy(deep=True)
    projgroup_to_resil_copy.loc[:, ['Resiliency Projects']] = 'no'
    projgroup_to_resil = pd.concat([projgroup_to_resil, projgroup_to_resil_copy], ignore_index=True)
    projgroup_to_resil = projgroup_to_resil.loc[:, ['Project Groups',
                                                    'Resiliency Projects']].drop_duplicates(ignore_index=True)
    hazard_levels = make_hazard_levels(model_params_file, logger)
    hazard_levels = hazard_levels.loc[:, ['Hazard Level', 'Hazard Event', 'Filename']]

    hazard_to_run = set(user_inputs['Hazard Events'].dropna().tolist())
    logger.config("List of hazard events for scenario builder: \t{}".format(', '.join(str(e) for e in hazard_to_run)))
    economic_to_run = set(user_inputs['Economic Scenarios'].dropna().tolist())
    logger.config(("List of economic scenarios for " +
                   "scenario builder: \t{}".format(', '.join(str(e) for e in economic_to_run))))
    elasticity_to_run = set(user_inputs['Trip Loss Elasticities'].dropna().tolist())
    logger.config(("List of trip elasticities for " +
                   "scenario builder: \t{}".format(', '.join(str(e) for e in elasticity_to_run))))
    resil_proj_to_run = set(user_inputs['Resiliency Projects'].dropna().tolist())
    resil_proj_to_run.add('no')
    logger.config("List of resilience projects for scenario builder: \t{}".format(', '.join(str(e) for e in resil_proj_to_run)))
    frequency_to_run = set(user_inputs['Event Frequency Factors'].dropna().tolist())
    logger.config(("List of event frequency factors for " +
                   "scenario builder: \t{}".format(', '.join(str(e) for e in frequency_to_run))))

    user_input_combos = list(product(economic_to_run, elasticity_to_run, frequency_to_run))
    user_input_combos.sort()

    product1 = pd.DataFrame(user_input_combos,
                            columns=['Economic', 'Trip Loss Elasticity', 'Future Event Frequency'])
    product1['IDScenarioNoHazard'] = np.arange(len(product1)) + 1
    logger.debug("Size of uncertainty scenario table without hazards or projects: {}".format(product1.shape))

    logger.debug("building out hazard recession possibilities")
    min_duration = cfg['min_duration']
    max_duration = cfg['max_duration']
    num_duration_cases = cfg['num_duration_cases']
    hazard_recov_type = cfg['hazard_recov_type']
    hazard_recov_length = cfg['hazard_recov_length']

    logger.config("Recovery Parameters: min duration = {} days, max duration = {} days".format(str(min_duration),
                                                                                               str(max_duration)))
    logger.config("Recovery Parameters: (maximum) number of hazard duration cases = {}".format(str(num_duration_cases)))
    logger.config(("Recovery Parameters: hazard recession length = " +
                   "{} {}".format(str(100 *
                                      hazard_recov_length if hazard_recov_type == 'percent' else hazard_recov_length),
                                  hazard_recov_type)))

    # build out initial hazard event duration possibilities, then calculate recession length for each possibility
    # NOTE: code below will round fractional intermediates, end result may not have exactly num_duration_cases values
    logger.warning("procedure for building out hazard recovery paths does not allow for fractional day lengths")
    durations = np.unique(np.linspace(min_duration, max_duration, num_duration_cases).astype(int))
    if hazard_recov_type == 'days':
        recessions = np.repeat(hazard_recov_length, len(durations)).astype(int)

    if hazard_recov_type == 'percent':
        recessions = np.around(durations * hazard_recov_length).astype(int)

    totals = durations + recessions

    logger.debug(("List of initial hazard event durations for " +
                  "scenario builder: \t{}".format(', '.join(str(e) for e in durations))))
    logger.debug(("List of corresponding recession durations for " +
                  "scenario builder: \t{}".format(', '.join(str(e) for e in recessions))))

    # hazard recovery path build out depends on hazard_recov_path_model
    # only option is 'Equal' (default)
    hazard_recov_path_model = cfg['hazard_recov_path_model']
    logger.config("{} hazard recovery path build out approach to be used".format(hazard_recov_path_model))

    # for each hazard event to run, use list of hazard levels to determine recession stages
    hazard_scenarios = pd.DataFrame(columns=['Initial Hazard Level', 'Total Duration', 'Exposure Recovery Path'])
    for i in hazard_to_run:
        for j in range(len(totals)):
            hazard_subset = hazard_levels[hazard_levels['Hazard Event'] == i]
            initial_hazard_level = hazard_subset['Hazard Level'].max()
            temp_row = {'Initial Hazard Level': initial_hazard_level, 'Total Duration': totals[j]}
            hazard_stages = hazard_subset.loc[hazard_subset['Hazard Level'] < initial_hazard_level, 'Hazard Level']

            init_path = np.repeat(initial_hazard_level, durations[j])
            if hazard_recov_path_model == 'equal':
                recess_path = hazard_stages.iloc[
                    np.around(np.linspace(0, 1, recessions[j]) * (len(hazard_stages) - 1))].to_numpy()
            else:
                logger.warning(("Should not have reached this point in the code, " +
                                "but placeholder for now for all other hazard recovery path models besides 'Equal'."))

            temp_row['Exposure Recovery Path'] = ",".join([str(element) for element in init_path.astype(int)])
            if len(recess_path) > 0:
                temp_row['Exposure Recovery Path'] = temp_row['Exposure Recovery Path'] + "," + \
                                                     ",".join([str(element) for element in recess_path.astype(int)])

            hazard_scenarios = hazard_scenarios.append(temp_row, ignore_index=True)

    # create cross product of two data frames to produce all possible uncertainty scenarios
    product2 = product1.assign(key=1).merge(hazard_scenarios.assign(key=1), on='key').drop(labels='key', axis=1)
    product2['ID-Uncertainty Scenario'] = np.arange(len(product2)) + 1
    logger.debug("Size of full uncertainty scenario table: {}".format(product2.shape))

    # remove unused project groups from lookup table before merge in order to avoid pulling in all 'no' baselines
    temp_proj = resil_proj_to_run.copy()
    temp_proj.remove('no')
    temp_group = projgroup_to_resil.loc[projgroup_to_resil['Resiliency Projects'].isin(temp_proj), 'Project Groups'].tolist()
    projgroup_to_resil = projgroup_to_resil.loc[projgroup_to_resil['Project Groups'].isin(temp_group), :]

    # merge with project groups and resilience projects
    product3 = product2.assign(key=1).merge(pd.DataFrame(resil_proj_to_run,
                                                         columns=['Resiliency Project']).assign(key=1),
                                            on='key').drop(labels='key', axis=1)
    product4 = pd.merge(product3, projgroup_to_resil, how='left',
                        left_on='Resiliency Project', right_on='Resiliency Projects',
                        indicator=True)
    logger.debug(("Number of resilience projects not matched to project " +
                  "groups: {}".format(sum(product4['_merge'] == 'left_only'))))
    if sum(product4['_merge'] == 'left_only') > 0:
        logger.warning(("TABLE JOIN WARNING: Some resilience projects in UserInputs.xlsx were not " +
                        "found in ProjectGroups tab of Model_Parameters.xlsx and will be excluded in analysis."))
    product4 = product4.loc[product4['_merge'] == 'both', :]
    product4.drop(labels=['Resiliency Projects', '_merge'], axis=1, inplace=True)
    product4.rename({'Project Groups': 'Project Group'}, axis='columns', inplace=True)
    product4['ID-Resiliency-Scenario'] = np.arange(len(product4)) + 1

    baseline_scenarios = product4[product4['Resiliency Project'] == 'no']

    scenario_input = pd.merge(product4,
                              baseline_scenarios.loc[:, ['ID-Uncertainty Scenario', 'Project Group',
                                                         'ID-Resiliency-Scenario']],
                              how='left', on=['ID-Uncertainty Scenario', 'Project Group'], suffixes=(None, "-Baseline"))
    logger.debug("Size of full uncertainty scenario table with resilience projects: {}".format(scenario_input.shape))

    with open(uncertainty_scenarios_file, "w", newline='') as f:
        scenario_input.to_csv(f, index=False)
        logger.result("Uncertainty scenario table written to {}".format(uncertainty_scenarios_file))

    logger.debug("extending uncertainty scenario table into hazard recovery path snapshots")
    extended_scenarios = pd.DataFrame()

    for index, row in scenario_input.iterrows():
        rs_id = str(row['ID-Resiliency-Scenario'])
        recov_path = str(row['Exposure Recovery Path'])

        # split recov_path by commas, e.g., "2,2,1,1" -> [2, 2, 1, 1]
        # terminating 0 representing no-hazard state is not included in hazard recovery path
        recov_path_list = recov_path.split(",")

        # build out hazard recovery path snapshots
        # keep track of damage, repair costs, and repair times in initial_stages
        # keep track of hazard recovery path in extended_scenarios
        stage_num = 0
        recov_path_tracker = []
        for i in recov_path_list:
            # keep track of (1) unique values in recov_path_list, (2) number of days each unique value repeats
            # create new rows per the number of unique values while updating exposure_level
            # use primary key of rs_id + "." + hazard event stage ID
            if i not in recov_path_tracker:
                stage_num += 1
                recov_path_tracker.append(i)
                # explicitly deepcopy to avoid overwriting variable row
                # (https://stackoverflow.com/questions/2465921/how-to-copy-a-dictionary-and-only-edit-the-copy)
                temp_stage = copy.deepcopy(row)
                curr_stage = rs_id + "." + str(stage_num)
                temp_stage['ID-Resiliency-Scenario-Stage'] = curr_stage
                temp_stage['Stage Number'] = stage_num
                temp_stage['Exposure Level'] = i
                temp_stage['Stage Duration'] = 1
                extended_scenarios = extended_scenarios.append(temp_stage, ignore_index=True)
            else:
                extended_scenarios.loc[extended_scenarios['ID-Resiliency-Scenario-Stage'] == curr_stage,
                                       'Stage Duration'] += 1

    # make sure 'Initial Hazard Level' and 'Stage Number' fields are integers
    extended_scenarios['Initial Hazard Level'] = extended_scenarios['Initial Hazard Level'].astype(int)
    extended_scenarios['Stage Number'] = extended_scenarios['Stage Number'].astype(int)

    # print out extended_scenarios as csv file
    extended_scenarios_file = os.path.join(output_folder, 'extended_scenarios_' + str(cfg['run_id']) + '.csv')
    logger.debug("Size of extended uncertainty scenario snapshot table: {}".format(extended_scenarios.shape))
    with open(extended_scenarios_file, "w", newline='') as f:
        extended_scenarios.to_csv(f, index=False)
        logger.result("Extended uncertainty scenario snapshot table written to {}".format(extended_scenarios_file))

    logger.info("creating table for repair costs and times")

    # keep track of initial hazard event levels for damage repair costs/times
    initial_stages = extended_scenarios[extended_scenarios['Stage Number'] == 1]
    # look-up only needed for subset of initial_stages with project-asset specified
    initial_stages = initial_stages[initial_stages['Resiliency Project'] != 'no']

    # read in tables mapping ID-Resiliency-Scenario to repair costs and times
    # default 'Category' choices are "Bridge", "Highway", and "Transit"

    # damage on resilience project network links depends on mitigation impact
    # options are 'binary' (default), 'manual'
    # if resil mitigation approach is manual, read in Exposure Reduction field as well
    # if a cell is left blank in Exposure Reduction field then assume no reduction on the link
    resil_mitigation_approach = cfg['resil_mitigation_approach']
    logger.config("{} resilience project mitigation approach to be used".format(resil_mitigation_approach))
    if resil_mitigation_approach == 'binary':
        projects = pd.read_csv(project_table, usecols=['Project ID', 'link_id', 'Category'],
                               converters={'Project ID': str, 'link_id': int, 'Category': str})
        # NOTE: use 99999 to denote complete mitigation
        projects['Exposure Reduction'] = 99999.0
    elif resil_mitigation_approach == 'manual':
        projects = pd.read_csv(project_table, usecols=['Project ID', 'link_id', 'Category', 'Exposure Reduction'],
                               converters={'Project ID': str, 'link_id': int, 'Category': str, 'Exposure Reduction': float})
    else:
        logger.error("Invalid option selected for resilience mitigation approach.")
        raise Exception("Variable resil_mitigation_approach must be set to 'binary' or 'manual'.")

    # catch any empty values in Exposure Reduction field and set to 0 reduction
    projects['Exposure Reduction'] = projects['Exposure Reduction'].fillna(0)
    projects.drop_duplicates(subset=['Project ID', 'link_id'], inplace=True, ignore_index=True)
    logger.debug("Size of input project table: {}".format(projects.shape))

    networks_list = initial_stages.loc[:, ['Project Group', 'Economic']].drop_duplicates(ignore_index=True)
    networks_list['Filename'] = networks_list['Economic'] + networks_list['Project Group'] + '.csv'
    network = pd.DataFrame()
    for index, row in networks_list.iterrows():
        if not os.path.exists(os.path.join(networks_folder, row['Filename'])):
            logger.error("NETWORK FILE ERROR: {} could not be found".format(os.path.join(networks_folder,
                                                                                         row['Filename'])))
            raise Exception("NETWORK FILE ERROR: {} could not be found".format(os.path.join(networks_folder,
                                                                                            row['Filename'])))
        temp_network = pd.read_csv(os.path.join(networks_folder, row['Filename']),
                                   usecols=['link_id', 'length', 'lanes', 'facility_type'],
                                   converters={'link_id': int, 'length': float, 'lanes': int, 'facility_type': str})
        temp_network.rename({'length': 'DISTANCE', 'lanes': 'LANES', 'facility_type': 'FACTYPE'},
                            axis='columns', inplace=True)
        temp_network['Project Group'] = row['Project Group']
        temp_network['Economic'] = row['Economic']
        network = network.append(temp_network, ignore_index=True)
    logger.debug("Size of input network table: {}".format(network.shape))

    depths_list = list(set(initial_stages['Exposure Level'].dropna().tolist()))
    depths_list = pd.merge(pd.DataFrame(depths_list, columns=['Hazard Level']),
                           hazard_levels.loc[:, ['Hazard Level', 'Filename']].astype(str), how='left',
                           on='Hazard Level')
    depths = pd.DataFrame()
    for index, row in depths_list.iterrows():
        filename = str(row['Filename']) + '.csv'
        if not os.path.exists(os.path.join(exposures_folder, filename)):
            logger.error("HAZARD EXPOSURE FILE ERROR: {} could not be found".format(os.path.join(exposures_folder,
                                                                                                 filename)))
            raise Exception("HAZARD EXPOSURE FILE ERROR: {} could not be found".format(os.path.join(exposures_folder,
                                                                                                    filename)))
        temp_depths = pd.read_csv(os.path.join(exposures_folder, filename),
                                  usecols=['link_id', cfg['exposure_field']],
                                  converters={'link_id': int, cfg['exposure_field']: float})
        temp_depths.drop_duplicates(subset=['link_id'], inplace=True, ignore_index=True)
        # catch any empty values in exposure field and set to 0 exposure
        temp_depths[cfg['exposure_field']] = temp_depths[cfg['exposure_field']].fillna(0)
        temp_depths['Exposure Level'] = row['Hazard Level']
        depths = depths.append(temp_depths, ignore_index=True)
    logger.debug("Size of input exposure table: {}".format(depths.shape))

    # NOTE: 'Exposure Reduction' field merged implicitly, used for damage calculation
    merged1 = pd.merge(initial_stages, projects, how='left', left_on='Resiliency Project', right_on='Project ID',
                       indicator=True)
    logger.debug("merged1 dimensions: {}".format(merged1.shape))
    logger.debug(("Number of uncertainty scenario projects not found in " +
                  "projects table: {}".format(sum(merged1['_merge'] == 'left_only'))))
    if sum(merged1['_merge'] == 'left_only') == merged1.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with projects table " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with projects table " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged1.drop(labels=['_merge'], axis=1, inplace=True)

    merged2 = pd.merge(merged1, network, how='left', on=['link_id', 'Project Group', 'Economic'], indicator=True)
    logger.debug("merged2 dimensions: {}".format(merged2.shape))
    logger.debug(("Number of project network links not found in " +
                  "network table: {}".format(sum(merged2['_merge'] == 'left_only'))))
    logger.debug(("Missing project network links " +
                  "by category: {}".format(merged2[merged2['_merge'] == 'left_only']['Category'].value_counts())))
    if sum(merged2['_merge'] == 'left_only') == merged2.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with network table " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with network table " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged2.drop(labels=['_merge'], axis=1, inplace=True)

    merged3 = pd.merge(merged2, depths.loc[:, ['link_id', 'Exposure Level', cfg['exposure_field']]], how='left',
                       on=['link_id', 'Exposure Level'], indicator=True)
    logger.debug("merged3 dimensions: {}".format(merged3.shape))
    logger.debug(("Number of hazard event + network link combinations not found in " +
                  "exposure table: {}".format(sum(merged3['_merge'] == 'left_only'))))
    if sum(merged3['_merge'] == 'left_only') == merged3.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with exposure table " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with exposure table " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged3.drop(labels=['_merge'], axis=1, inplace=True)

    # calculate damage, repair cost, repair time for both baseline and resilience scenarios
    # update exposure values for network links associated with the resilience project
    # damage on resilience project network links depends on mitigation impact
    logger.debug("calculating resilience project exposure with reduction")
    merged3['baseline_exposure'] = merged3[cfg['exposure_field']]
    merged3['project_exposure'] = merged3[cfg['exposure_field']] - merged3['Exposure Reduction']
    merged3.loc[merged3['project_exposure'] < 0, ['project_exposure']] = 0

    # exposure-damage approach based on exposure_grid_overlay.py helper tool
    # current options are 'binary', 'default_damage_table', 'manual'
    exposure_damage_approach = cfg['exposure_damage_approach']
    logger.config("{} exposure-damage approach to be used".format(exposure_damage_approach))

    if exposure_damage_approach == 'binary':
        # use binary case where if exposure value > 0 then 'Damage (%)' = 1, else 'Damage (%)' = 0
        merged4 = merged3.copy(deep=True)
        merged4['baseline_damage'] = 0
        merged4.loc[merged4['baseline_exposure'] > 0, ['baseline_damage']] = 1
        merged4.loc[merged4['baseline_exposure'].isna(), ['baseline_damage']] = np.NaN
        merged4['project_damage'] = 0
        merged4.loc[merged4['project_exposure'] > 0, ['project_damage']] = 1
        merged4.loc[merged4['project_exposure'].isna(), ['project_damage']] = np.NaN

    if exposure_damage_approach == 'default_damage_table':
        # use default depth-damage table for flood-based hazards adapted from IRQI prototype (Simonovic et al.)
        exposure_unit = cfg['exposure_unit']
        # Convert exposure units to feet
        if exposure_unit.lower() in ['feet', 'ft', 'foot']:
            merged3['baseline_value'] = merged3['baseline_exposure'] * 1.0
            merged3['project_value'] = merged3['project_exposure'] * 1.0
        if exposure_unit.lower() in ['yards', 'yard']:
            merged3['baseline_value'] = merged3['baseline_exposure'] * 3.0
            merged3['project_value'] = merged3['project_exposure'] * 3.0
        if exposure_unit.lower() in ['meters', 'm']:
            merged3['baseline_value'] = merged3['baseline_exposure'] * 3.28
            merged3['project_value'] = merged3['project_exposure'] * 3.28

        damage_table = os.path.join(os.path.abspath(os.path.join(os.getcwd(), os.pardir)), 'config',
                                    'default_exposure-damage_table.csv')
        if not os.path.exists(damage_table):
            logger.error("DEFAULT DAMAGE TABLE FILE ERROR: {} could not be found".format(damage_table))
            raise Exception("DEFAULT DAMAGE TABLE FILE ERROR: {} could not be found".format(damage_table))
        damages = pd.read_csv(damage_table, usecols=['Asset Type', 'min_exposure', 'max_exposure', 'Damage (%)'],
                              converters={'Asset Type': str, 'min_exposure': float,
                                          'max_exposure': float, 'Damage (%)': float})

        # units for default depth-damage table is feet
        # look up 'Damage (%)' for each network link based on 'min_exposure' and 'max_exposure'
        # look up for both baseline and resilience scenarios

        sqlcode_baseline = """
        select merged3.*, damages."Damage (%)" as baseline_damage
        from merged3
        left outer join damages
        on merged3."Category" = damages."Asset Type"
        and merged3."baseline_value" >= damages."min_exposure"
        and merged3."baseline_value" < damages."max_exposure"
        """
        temp = pandasql.sqldf(sqlcode_baseline, locals())
        sqlcode_project = """
        select temp.*, damages."Damage (%)" as project_damage
        from temp
        left outer join damages
        on temp."Category" = damages."Asset Type"
        and temp."project_value" >= damages."min_exposure"
        and temp."project_value" < damages."max_exposure"
        """
        merged4 = pandasql.sqldf(sqlcode_project, locals())

    if exposure_damage_approach == 'manual':
        # use user-defined exposure-damage table with structure similar to default_damage_table
        # exposure-damage table has a clearly defined structure with distinct rows for each asset type
        # units for exposure inputs files and exposure-damage table must match
        merged3['baseline_value'] = merged3['baseline_exposure'] * 1.0
        merged3['project_value'] = merged3['project_exposure'] * 1.0

        exposure_damage_csv = cfg['exposure_damage_csv']
        if not os.path.exists(exposure_damage_csv):
            logger.error("USER-DEFINED DAMAGE TABLE FILE ERROR: {} could not be found".format(exposure_damage_csv))
            raise Exception("USER-DEFINED DAMAGE TABLE FILE ERROR: {} could not be found".format(exposure_damage_csv))
        damages = pd.read_csv(exposure_damage_csv, usecols=['Asset Type', 'min_exposure', 'max_exposure', 'Damage (%)'],
                              converters={'Asset Type': str, 'min_exposure': float,
                                          'max_exposure': float, 'Damage (%)': float})

        # look up 'Damage (%)' for each network link based on 'min_exposure' and 'max_exposure'
        # look up for both baseline and resilience scenarios
        sqlcode_baseline = """
        select merged3.*, damages."Damage (%)" as baseline_damage
        from merged3
        left outer join damages
        on merged3."Category" = damages."Asset Type"
        and merged3."baseline_value" >= damages."min_exposure"
        and merged3."baseline_value" < damages."max_exposure"
        """
        temp = pandasql.sqldf(sqlcode_baseline, locals())
        sqlcode_project = """
        select temp.*, damages."Damage (%)" as project_damage
        from temp
        left outer join damages
        on temp."Category" = damages."Asset Type"
        and temp."project_value" >= damages."min_exposure"
        and temp."project_value" < damages."max_exposure"
        """
        merged4 = pandasql.sqldf(sqlcode_project, locals())

    # ensure 'project_damage' values equal 0 for resilience project network links in binary case
    # or network links given value 99999 for Exposure Reduction in manual case
    if resil_mitigation_approach == 'binary':
        # use binary case where if link is associated with resilience project (e.g., all the ones tracked) then 'project_damage' = 0
        merged4['project_damage'] = 0
    elif resil_mitigation_approach == 'manual':
        # for manual case if link is assigned 99999 by user then 'project_damage' = 0
        merged4['project_damage'] = np.where(merged4['Exposure Reduction'] == 99999.0, 0, merged4['project_damage'])

    logger.debug("merged4 dimensions: {}".format(merged4.shape))
    logger.debug(("Number of exposure values missing baseline damage percent " +
                  "values: {}".format(merged4[merged4['baseline_damage'].isnull()].shape[0])))
    logger.debug(("Number of exposure values missing project damage percent " +
                  "values: {}".format(merged4[merged4['project_damage'].isnull()].shape[0])))

    # merge with repair_cost_table and repair_time_table

    # current options are 'default', 'user-defined'
    repair_cost_approach = cfg['repair_cost_approach']
    logger.config("{} repair-cost approach to be used".format(repair_cost_approach))

    # compare to copy of 'FACTYPE' to preserve original 'FACTYPE' field
    merged4['cost_type'] = merged4['FACTYPE']

    if repair_cost_approach == 'default':
        # use default repair cost look-up table
        repair_cost_table = os.path.join(os.path.abspath(os.path.join(os.getcwd(), os.pardir)), 'config',
                                         'default_repair-cost_table.csv')
        if not os.path.exists(repair_cost_table):
            logger.error("DEFAULT REPAIR COST FILE ERROR: {} could not be found".format(repair_cost_table))
            raise Exception("DEFAULT REPAIR COST FILE ERROR: {} could not be found".format(repair_cost_table))
        costs = pd.read_csv(repair_cost_table,
                            usecols=['Asset Type', 'Network Type', 'Facility Type',
                                     'Damage Repair Cost', 'Total Repair Cost'],
                            converters={'Asset Type': str, 'Network Type': str, 'Facility Type': str,
                                        'Damage Repair Cost': float, 'Total Repair Cost': float})
        repair_network_type = cfg['repair_network_type']
        costs = costs[(costs['Asset Type'] == 'Bridge') | (costs['Asset Type'] == 'Transit') | (costs['Network Type'] == repair_network_type)]

    elif repair_cost_approach == 'user-defined':
        # use user-defined repair cost look-up table
        # repair cost look-up table matches 'Asset Type' to 'Category' in project table CSV
        # repair cost look-up table matches 'Facility Type' to 'facility_type' in link CSV
        repair_cost_table = cfg['repair_cost_csv']
        if not os.path.exists(repair_cost_table):
            logger.error("USER-DEFINED REPAIR COST FILE ERROR: {} could not be found".format(repair_cost_table))
            raise Exception("USER-DEFINED REPAIR COST FILE ERROR: {} could not be found".format(repair_cost_table))
        costs = pd.read_csv(repair_cost_table,
                            usecols=['Asset Type', 'Facility Type', 'Damage Repair Cost', 'Total Repair Cost'],
                            converters={'Asset Type': str, 'Facility Type': str, 'Damage Repair Cost': float,
                                        'Total Repair Cost': float})
    else:
        logger.error("Invalid option selected for repair cost approach.")
        raise Exception("Variable repair_cost_approach must be set to 'default' or 'user-defined'.")
    logger.config("Using repair cost file: {}".format(repair_cost_table))
    logger.debug("Size of input repair cost table: {}".format(costs.shape))

    # 'cost_type' values derived from network file should match up with 'Facility Type' in repair cost table
    # for each 'Category'/'Asset Type'
    merged5 = pd.merge(merged4,
                       costs.loc[:, ['Asset Type', 'Facility Type', 'Damage Repair Cost', 'Total Repair Cost']],
                       how='left', left_on=['Category', 'cost_type'], right_on=['Asset Type', 'Facility Type'],
                       indicator=True)
    logger.debug("merged5 dimensions: {}".format(merged5.shape))
    # NOTE: below are some queries for debugging
    # merged5[merged5['Damage Repair Cost'].isnull()]
    # merged5[merged5['Total Repair Cost'].isnull()]
    # merged5.loc[merged5['Damage Repair Cost'].isnull(), ['Category', 'FACTYPE']].drop_duplicates()
    # merged5.loc[merged5['Total Repair Cost'].isnull(), ['Category', 'FACTYPE']].drop_duplicates()
    logger.debug(("Number of network links not found in " +
                  "repair cost table: {}".format(sum(merged5['_merge'] == 'left_only'))))
    if sum(merged5['_merge'] == 'left_only') == merged5.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with repair cost table " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with repair cost table " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged5.drop(labels=['_merge'], axis=1, inplace=True)
    # calculate for both baseline and resilience scenarios
    merged5['baseline_damage_repair_cost'] = merged5['Damage Repair Cost'] * merged5['baseline_damage']
    merged5['baseline_total_repair_cost'] = merged5['Total Repair Cost'] * merged5['baseline_damage']
    merged5['project_damage_repair_cost'] = merged5['Damage Repair Cost'] * merged5['project_damage']
    merged5['project_total_repair_cost'] = merged5['Total Repair Cost'] * merged5['project_damage']

    # current options are 'default', 'user-defined'
    repair_time_approach = cfg['repair_time_approach']
    logger.config("{} repair-time approach to be used".format(repair_time_approach))

    if repair_time_approach == 'default':
        # use default repair time look-up table
        repair_time_table = os.path.join(os.path.abspath(os.path.join(os.getcwd(), os.pardir)), 'config',
                                         'default_repair-time_table.csv')
    elif repair_time_approach == 'user-defined':
        # use user-defined repair time look-up table
        # repair time look-up table matches 'Asset Type' to 'Category' in project table CSV
        # repair time look-up table sorts 'repair_category' (see below for definition) between 'min_inclusive' and 'max_exclusive'
        repair_time_table = cfg['repair_time_csv']
    else:
        logger.error("Invalid option selected for repair time approach.")
        raise Exception("Variable repair_time_approach must be set to 'default' or 'user-defined'.")
    logger.config("Using repair time file: {}".format(repair_time_table))
    if not os.path.exists(repair_time_table):
        logger.error("REPAIR TIME FILE ERROR: {} could not be found".format(repair_time_table))
        raise Exception("REPAIR TIME FILE ERROR: {} could not be found".format(repair_time_table))
    times = pd.read_csv(repair_time_table,
                        usecols=['Asset Type', 'min_inclusive', 'max_exclusive', 'repair_time'],
                        converters={'Asset Type': str, 'min_inclusive': float, 'max_exclusive': float,
                                    'repair_time': float})
    logger.debug("Size of input repair time table: {}".format(times.shape))

    # look up 'repair_time' for each network link based on 'min_inclusive' and 'max_exclusive' and 'Asset Type'
    # NOTE: currently 'repair_category' is created in code
    # 'repair_category' field equals (1) float('FACTYPE') if 'Category' = 'Highway' or 'Transit' (or other asset type),
    # (2) (only if default) sum of 'DISTANCE' (in ft) across 'Bridge' network links for each
    # 'ID-Resiliency-Scenario-Stage' if 'Category' = 'Bridge'
    asset_lengths = merged5.loc[:, ['ID-Resiliency-Scenario-Stage', 'Category',
                                    'DISTANCE']].groupby(by=['ID-Resiliency-Scenario-Stage', 'Category'],
                                                         as_index=False, sort=False).sum()
    asset_lengths.rename({'DISTANCE': 'Project-Asset Distance'}, axis='columns', inplace=True)
    num_rows = merged5.shape[0]
    merged5 = pd.merge(merged5, asset_lengths, how='left', on=['ID-Resiliency-Scenario-Stage', 'Category'])
    if merged5.shape[0] != num_rows:
        logger.warning("Table join to asset_lengths in calculating repair time is not unique")
    # compare to copy of 'FACTYPE' to preserve original 'FACTYPE' field
    merged5['repair_category'] = pd.to_numeric(merged5['FACTYPE'], errors='coerce')
    # compare to 'Project-Asset Distance' converted from mi to ft for 'Bridge' in default repair time case
    if repair_time_approach == 'default':
        merged5['repair_category'] = np.where(merged5['Category'] == 'Bridge',
                                              5280.0 * merged5['Project-Asset Distance'],
                                              merged5['repair_category'])

    # NOTE: merge that has 'repair_category' = NaN between min_inclusive and max_exclusive leads to NaN generated
    sqlcode = """
    select merged5.*, times."repair_time"
    from merged5
    left outer join times
    on merged5."Category" = times."Asset Type"
    and merged5."repair_category" >= times."min_inclusive"
    and merged5."repair_category" < times."max_exclusive"
    """
    merged6 = pandasql.sqldf(sqlcode, locals())
    # adjust 'repair_time' by 'Damage (%)'
    # calculate for both baseline and resilience scenarios
    merged6['baseline_repair_time'] = merged6['repair_time'] * merged6['baseline_damage']
    merged6['project_repair_time'] = merged6['repair_time'] * merged6['project_damage']
    logger.debug("merged6 dimensions: {}".format(merged6.shape))
    # NOTE: below are some queries for debugging
    # merged6[merged6['FEDFUNC'].isnull()]
    # merged6[merged6['repair_category'].isnull()]
    # merged6.loc[merged6['repair_time'].isnull(), ['Category', 'FEDFUNC']].drop_duplicates()
    # merged6.loc[merged6['repair_time'].isnull(), ['Category', 'repair_category']].drop_duplicates()
    logger.debug(("Number of network links missing baseline " +
                  "repair time values: {}".format(merged6[merged6['baseline_repair_time'].isnull()].shape[0])))
    logger.debug(("Number of network links missing project " +
                  "repair time values: {}".format(merged6[merged6['project_repair_time'].isnull()].shape[0])))

    repair_calculator_file = os.path.join(output_folder, 'repair_calculator_' + str(cfg['run_id']) + '.csv')
    with open(repair_calculator_file, "w", newline='') as f:
        logger.result("Repair cost and time lookup table written to {}".format(repair_calculator_file))
        merged6.to_csv(f, index=False)

    # calculate for both baseline and resilience scenarios
    # calculate total repair costs and average damage percent and average repair time for each project-asset ID
    # general assumption is repair costs will be by lane-mile for all non-'Bridge' asset types (which are by sq ft)
    # NOTE: NaN values for 'damage_repair', 'total_repair', 'Damage (%)', and 'repair_time' are replaced by 0
    # total repair costs are (non-bridge cost * distance (mi) * lanes * damage % (already incorporated) + bridge cost *
    # area (sq ft) * damage % (already incorporated)) summed across links per 'ID-Resiliency-Scenario-Stage'
    # bridge area calculated as distance (ft) * lanes * 12 ft lane width
    merged6['baseline_damage_repair'] = np.where(merged6['Category'] == 'Bridge',
                                                 5280.0 * merged6['DISTANCE'] * 12.0 * merged6['LANES'] *
                                                 merged6['baseline_damage_repair_cost'].astype(float),
                                                 merged6['DISTANCE'] * merged6['LANES'] *
                                                 merged6['baseline_damage_repair_cost'].astype(float))
    merged6['baseline_damage_repair'] = merged6['baseline_damage_repair'].fillna(0)
    merged6['project_damage_repair'] = np.where(merged6['Category'] == 'Bridge',
                                                5280.0 * merged6['DISTANCE'] * 12.0 * merged6['LANES'] *
                                                merged6['project_damage_repair_cost'].astype(float),
                                                merged6['DISTANCE'] * merged6['LANES'] *
                                                merged6['project_damage_repair_cost'].astype(float))
    merged6['project_damage_repair'] = merged6['project_damage_repair'].fillna(0)
    merged6['baseline_total_repair'] = np.where(merged6['Category'] == 'Bridge',
                                                5280.0 * merged6['DISTANCE'] * 12.0 * merged6['LANES'] *
                                                merged6['baseline_total_repair_cost'].astype(float),
                                                merged6['DISTANCE'] * merged6['LANES'] *
                                                merged6['baseline_total_repair_cost'].astype(float))
    merged6['baseline_total_repair'] = merged6['baseline_total_repair'].fillna(0)
    merged6['project_total_repair'] = np.where(merged6['Category'] == 'Bridge',
                                               5280.0 * merged6['DISTANCE'] * 12.0 * merged6['LANES'] *
                                               merged6['project_total_repair_cost'].astype(float),
                                               merged6['DISTANCE'] * merged6['LANES'] *
                                               merged6['project_total_repair_cost'].astype(float))
    merged6['project_total_repair'] = merged6['project_total_repair'].fillna(0)
    cost_summary = merged6.loc[:, ['ID-Resiliency-Scenario-Stage', 'baseline_damage_repair', 'project_damage_repair',
                                   'baseline_total_repair', 'project_total_repair']].groupby('ID-Resiliency-Scenario-Stage', as_index=False,
                                                                                             sort=False).sum()

    merged6['baseline_damage'] = merged6['baseline_damage'].fillna(0)
    merged6['project_damage'] = merged6['project_damage'].fillna(0)
    merged6['baseline_repair_time'] = merged6['baseline_repair_time'].fillna(0)
    merged6['project_repair_time'] = merged6['project_repair_time'].fillna(0)
    time_summary = merged6.loc[:, ['ID-Resiliency-Scenario-Stage', 'baseline_damage', 'project_damage', 'baseline_repair_time',
                                   'project_repair_time']].groupby('ID-Resiliency-Scenario-Stage', as_index=False,
                                                                   sort=False).mean()

    # NOTE: for partial damage recovery functionality, could group links in a scenario-project by repair_time to build
    #  damage recovery path instead of reporting an average repair_time across links (also could weight by distance)
    #  but would prefer to not add core model runs for groups of links being repaired sequentially
    # NOTE: possible core model runs to do include: complete mitigation + hazard, user-specified repair stages

    # match scenario-level repair costs and times back to initial_scenarios data frame
    merged7 = pd.merge(initial_stages, cost_summary, how='left', on='ID-Resiliency-Scenario-Stage', indicator=True)
    logger.debug("merged7 dimensions: {}".format(merged7.shape))
    logger.debug(("Unable to calculate repair costs for " +
                  "{} uncertainty scenarios".format(sum(merged7['_merge'] == 'left_only'))))
    if sum(merged7['_merge'] == 'left_only') == merged7.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with calculated repair costs " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with calculated repair costs " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged7.drop(labels=['_merge'], axis=1, inplace=True)
    merged8 = pd.merge(merged7, time_summary, how='left', on='ID-Resiliency-Scenario-Stage', indicator=True)
    logger.debug("merged8 dimensions: {}".format(merged8.shape))
    logger.debug(("Unable to calculate repair times for " +
                  "{} uncertainty scenarios".format(sum(merged8['_merge'] == 'left_only'))))
    if sum(merged8['_merge'] == 'left_only') == merged8.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with calculated repair times " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with calculated repair times " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged8.drop(labels=['_merge'], axis=1, inplace=True)

    # scenario-level output file
    repair_output_file = os.path.join(output_folder, 'scenario_repair_output_' + str(cfg['run_id']) + '.csv')
    logger.debug("Size of repair output table: {}".format(merged8.shape))
    with open(repair_output_file, "w", newline='') as f:
        logger.result("Output table for repair cost and time module written to {}".format(repair_output_file))
        merged8.to_csv(f, index=False)

    logger.info("Finished: recovery initialization module")


# ==============================================================================


def check_user_inputs_coverage(user_inputs_file, model_params_file, input_folder, logger):
    logger.info("Start: check_user_inputs_coverage")
    is_covered = 1

    # if params_file is "UserInputs.xlsx" then sheet_name = 'UserInputs'
    model_params = pd.read_excel(user_inputs_file, sheet_name='UserInputs',
                                 usecols=['Hazard Events', 'Economic Scenarios', 'Resiliency Projects'],
                                 converters={'Hazard Events': str, 'Economic Scenarios': str, 'Resiliency Projects': str})
    projgroup_to_resil = pd.read_excel(model_params_file, sheet_name='ProjectGroups',
                                       converters={'Project Groups': str, 'Resiliency Projects': str})
    projgroup_to_resil = projgroup_to_resil.loc[projgroup_to_resil['Resiliency Projects'] != 'no', ['Project Groups', 'Resiliency Projects']]
    hazard_events = pd.read_excel(model_params_file, sheet_name='Hazards',
                                  usecols=['Hazard Event', 'Filename'],
                                  converters={'Hazard Event': str, 'Filename': str})

    # read in columns 'Hazard Events', 'Economic Scenarios', 'Resiliency Projects'
    # do not check resilience project coverage
    hazard = set(model_params['Hazard Events'].dropna().tolist())
    socio = set(model_params['Economic Scenarios'].dropna().tolist())
    resil = set(model_params['Resiliency Projects'].dropna().tolist())
    resil.discard('no')
    projgroup = projgroup_to_resil.loc[projgroup_to_resil['Resiliency Projects'].isin(resil), 'Project Groups'].tolist()

    # check exposure CSV files, network CSV files (do not check demand OMX files)
    # do not check base year or future year metamodel coverage here; check in rdr_RecoveryAnalysis.py
    hazards_list = pd.merge(pd.DataFrame(hazard, columns=['Hazard Event']),
                            hazard_events, how='left', on='Hazard Event')
    for index, row in hazards_list.iterrows():
        filename = os.path.join(input_folder, 'Hazards', str(row['Filename']) + '.csv')
        if not os.path.exists(filename):
            is_covered = 0
            logger.error("Missing input file {}".format(filename))

    for i in socio:
        for j in projgroup:
            filename = os.path.join(input_folder, 'Networks', str(i) + str(j) + '.csv')
            if not os.path.exists(filename):
                is_covered = 0
                logger.error("Missing input file {}".format(filename))

    logger.info("Finished: check_user_inputs_coverage")
    return is_covered


# ==============================================================================


def make_hazard_levels(model_params_file, logger):
    logger.info("Start: make_hazard_levels")
    # version used for rdr_RecoveryAnalysis.py
    # hazard_levels = pd.read_excel(model_params_file, sheet_name='Hazards',
    #                              usecols=['Hazard Level', 'HazardDim1', 'HazardDim2', 'Hazard Event',
    #                                       'Recovery', 'Event Probability in Start Year'],
    #                              converters={'Hazard Level': int, 'HazardDim1': int, 'HazardDim2': int,
    #                                          'Hazard Event': str, 'Recovery': str,
    #                                          'Event Probability in Start Year': float})
    hazard_events = pd.read_excel(model_params_file, sheet_name='Hazards',
                                  usecols=['Hazard Event', 'Filename', 'HazardDim1', 'HazardDim2',
                                           'Event Probability in Start Year'],
                                  converters={'Hazard Event': str, 'Filename': str, 'HazardDim1': int, 'HazardDim2': int,
                                              'Event Probability in Start Year': float})
    model_params = pd.read_excel(model_params_file, sheet_name='UncertaintyParameters',
                                 usecols=['Recovery Stages'],
                                 converters={'Recovery Stages': str})
    # recovery stages are placed in ascending order as strings not numeric
    recovery = sorted(set(model_params['Recovery Stages'].dropna().tolist()))
    logger.config("List of recovery stages: \t{}".format(', '.join(str(e) for e in recovery)))

    hazard_levels = hazard_events.assign(key=1).merge(pd.DataFrame(recovery, columns=['Recovery']).assign(key=1),
                                                      on='key').drop(labels=['key'], axis=1)
    temp_hazard_levels = np.arange(len(hazard_levels)) + 1
    hazard_levels['Hazard Level'] = temp_hazard_levels[::-1]

    logger.info("Finished: make_hazard_levels")
    return hazard_levels
