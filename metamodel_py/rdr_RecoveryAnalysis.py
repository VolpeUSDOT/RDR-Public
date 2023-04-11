#!/usr/bin/env python
# coding: utf-8


# ---------------------------------------------------------------------------------------------------
# Name: rdr_RecoveryAnalysis
#
# Purpose: Reads in metamodel regression outputs. Aggregates metrics across hazard recovery period.
# Rolls up metrics across entire period of analysis. Calculates BCA and regret metrics.
#
# ---------------------------------------------------------------------------------------------------
import os
import copy
import shutil
import datetime
import zipfile
import numpy as np
import pandas as pd
from rdr_RecoveryInit import make_hazard_levels


def main(input_folder, output_folder, cfg, logger):
    logger.info("Start: recovery analysis module")

    logger.debug("reading in parameters for metamodel analysis")
    roi_analysis_type = cfg['roi_analysis_type']

    start_year = cfg['start_year']
    end_year = cfg['end_year']
    base_year = cfg['base_year']
    future_year = cfg['future_year']

    # cost inputs and outputs are reported in dollar_year units
    dollar_year = cfg['dollar_year']
    miles_cost = cfg['veh_oper_cost']
    hours_cost = cfg['vot_per_hour']
    vehicle_occupancy = cfg['vehicle_occupancy']
    discount_factor = cfg['discount_factor']

    # safety parameters
    fatality_rate = cfg['fatality_rate']
    injury_rate = cfg['injury_rate']
    pdo_rate = cfg['pdo_rate']
    safety_monetization_csv = cfg['safety_monetization_csv']

    # emissions parameters
    co2_rate = cfg['co2_rate']
    nox_rate = cfg['nox_rate']
    so2_rate = cfg['so2_rate']
    pm25_rate = cfg['pm25_rate']
    emissions_monetization_csv = cfg['emissions_monetization_csv']

    logger.config("ReportingParameters: ROI analysis type is {}".format(roi_analysis_type))
    logger.config("ReportingParameters: period of analysis is {} to {}".format(str(start_year), str(end_year)))
    logger.config(("ReportingParameters: base year runs are for year {}, ".format(str(base_year)) +
                   "future year runs are for year {}".format(str(future_year))))
    logger.config("ReportingParameters: monetary values are in units of year {} dollars".format(str(dollar_year)))
    logger.config("ReportingParameters: cost of vehicle-mile = ${}, cost of person-hour = ${}".format(str(miles_cost),
                                                                                                      str(hours_cost)))
    logger.config(("ReportingParameters: average vehicle occupancy = {}, ".format(str(vehicle_occupancy)) +
                   "discounting factor = {}".format(str(discount_factor))))
    logger.config("ReportingParameters: safety rates for fatality = {}, injury = {}, property damage only = {}".format(str(fatality_rate),
                                                                                                                       str(injury_rate),
                                                                                                                       str(pdo_rate)))
    logger.config("ReportingParameters: emissions rates for CO2 = {}, NOx = {}, SO2 = {}, PM2.5 = {}".format(str(co2_rate),
                                                                                                             str(nox_rate),
                                                                                                             str(so2_rate),
                                                                                                             str(pm25_rate)))

    # uncertainty scenario information, regression outputs, repair costs and times
    logger.debug("reading in output files from previous modules")
    scenarios_table = os.path.join(output_folder, 'uncertainty_scenarios_' + str(cfg['run_id']) + '.csv')
    if not os.path.exists(scenarios_table):
        logger.error("UNCERTAINTY SCENARIOS FILE ERROR: {} could not be found".format(scenarios_table))
        raise Exception("UNCERTAINTY SCENARIOS FILE ERROR: {} could not be found".format(scenarios_table))
    extended_table = os.path.join(output_folder, 'extended_scenarios_' + str(cfg['run_id']) + '.csv')
    if not os.path.exists(extended_table):
        logger.error("EXTENDED SCENARIOS FILE ERROR: {} could not be found".format(extended_table))
        raise Exception("EXTENDED SCENARIOS FILE ERROR: {} could not be found".format(extended_table))
    repair_table = os.path.join(output_folder, 'scenario_repair_output_' + str(cfg['run_id']) + '.csv')
    if not os.path.exists(repair_table):
        logger.error("SCENARIO REPAIR OUTPUT FILE ERROR: {} could not be found".format(repair_table))
        raise Exception("SCENARIO REPAIR OUTPUT FILE ERROR: {} could not be found".format(repair_table))

    # SP or RT run type specified in config file
    # NOTE: do not currently use lost trips, extra miles, extra hours, circuitous_trips_removed fields
    # NOTE: cfg['run_id'] not used in filename for base year metrics
    base_regression_table = os.path.join(input_folder,
                                         'Metamodel_scenarios_' + cfg['aeq_run_type'] + '_baseyear.csv')
    if not os.path.exists(base_regression_table):
        logger.error("BASE YEAR METAMODEL FILE ERROR: {} could not be found".format(base_regression_table))
        raise Exception("BASE YEAR METAMODEL FILE ERROR: {} could not be found".format(base_regression_table))
    future_regression_table = os.path.join(output_folder, 'Metamodel_scenarios_' + cfg['aeq_run_type'] +
                                           '_futureyear_' + str(cfg['run_id']) + '.csv')
    if not os.path.exists(future_regression_table):
        logger.error("FUTURE YEAR METAMODEL FILE ERROR: {} could not be found".format(future_regression_table))
        raise Exception("FUTURE YEAR METAMODEL FILE ERROR: {} could not be found".format(future_regression_table))

    master_table = pd.read_csv(scenarios_table)
    extended_scenarios = pd.read_csv(extended_table,
                                     converters={'Exposure Level': int, 'Economic': str, 'Project Group': str,
                                                 'Resiliency Project': str, 'Trip Loss Elasticity': float,
                                                 'Initial Hazard Level': int})
    repair_data = pd.read_csv(repair_table)
    base_regression_output = pd.read_csv(base_regression_table,
                                         converters={'hazard': str, 'recovery': str})
    future_regression_output = pd.read_csv(future_regression_table,
                                           converters={'socio': str, 'projgroup': str, 'resil': str,
                                                       'elasticity': float, 'hazard': str, 'recovery': str})

    logger.debug("Size of uncertainty scenario table: {}".format(master_table.shape))
    logger.debug("Size of extended scenario table: {}".format(extended_scenarios.shape))
    logger.debug("Size of regression outputs table for base year: {}".format(base_regression_output.shape))
    logger.debug("Size of regression outputs table for future year: {}".format(future_regression_output.shape))
    logger.debug("Size of repair costs and times table: {}".format(repair_data.shape))

    # auxiliary inputs - hazard level information, resilience project information
    model_params_file = os.path.join(input_folder, 'Model_Parameters.xlsx')
    if not os.path.exists(model_params_file):
        logger.error("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
        raise Exception("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
    hazard_levels = make_hazard_levels(model_params_file, logger)
    hazard_levels = hazard_levels.loc[:, ['Hazard Level', 'HazardDim1', 'HazardDim2', 'Hazard Event',
                                          'Recovery', 'Event Probability in Start Year']]
    logger.debug("Size of hazard information table: {}".format(hazard_levels.shape))

    project_table = os.path.join(input_folder, 'LookupTables', 'project_info.csv')
    if not os.path.exists(project_table):
        logger.error("RESILIENCE PROJECTS FILE ERROR: {} could not be found".format(project_table))
        raise Exception("RESILIENCE PROJECTS FILE ERROR: {} could not be found".format(project_table))
    projects = pd.read_csv(project_table, usecols=['Project ID', 'Project Name', 'Asset', 'Project Cost', 'Project Lifespan', 'Annual Maintenance Cost'],
                           converters={'Project ID': str, 'Project Name': str, 'Asset': str, 'Project Cost': str,
                                       'Project Lifespan': int, 'Annual Maintenance Cost': str})
    # convert 'Project Cost' and 'Annual Maintenance Cost' columns to float type
    projects['Estimated Project Cost'] = projects['Project Cost'].replace('[\$,]', '', regex=True).astype(float)
    projects['Estimated Maintenance Cost'] = projects['Annual Maintenance Cost'].replace('[\$,]', '', regex=True).astype(float)
    logger.debug("Size of resilience project information table: {}".format(projects.shape))

    # create table of unique project-asset rows
    project_list = projects.drop_duplicates(ignore_index=True)
    # row in project table is created for baseline 'no' case with Estimated Project Cost = 0
    temp_row = {'Project ID': 'no', 'Project Name': 'No Vulnerability Projects', 'Asset': 'None',
                'Estimated Project Cost': 0.0, 'Project Lifespan': end_year - start_year + 1,
                'Estimated Maintenance Cost': 0.0}
    project_list = project_list.append(temp_row, ignore_index=True)

    # calculate metrics for Tableau dashboard

    # combine all costs - resilience project investments, repair costs, indirect costs (trips, VMT, PHT)

    # merge extended_scenarios with hazard_levels in left outer merge on:
    # 'Exposure Level' = 'Hazard Level', pull in 'Hazard Event' and 'Recovery'
    logger.debug("matching regression outputs to extended scenarios")
    merged1 = pd.merge(extended_scenarios, hazard_levels.loc[:, ['Hazard Level', 'Hazard Event', 'Recovery']],
                       how='left', left_on='Exposure Level', right_on='Hazard Level', indicator=True)
    logger.debug(("Number of extended scenario snapshots not found in " +
                  "hazard levels table: {}".format(sum(merged1['_merge'] == 'left_only'))))
    if sum(merged1['_merge'] == 'left_only') > 0:
        logger.error(("TABLE JOIN ERROR: Join of extended scenarios with hazard levels table " +
                     "produced a mismatch. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of extended scenarios with hazard levels table " +
                         "produced a mismatch. Check the corresponding table columns."))
    merged1.drop(labels=['_merge'], axis=1, inplace=True)

    # merge with future_regression_output in left outer merge on:
    # 'Economic' = 'socio', 'Project Group' = 'projgroup', 'Resiliency Project' = 'resil',
    # 'Trip Loss Elasticity' = 'elasticity', 'Hazard Event' = 'hazard', 'Recovery' = 'recovery'
    merged2 = pd.merge(merged1, future_regression_output, how='left',
                       left_on=['Economic', 'Project Group', 'Resiliency Project',
                                'Trip Loss Elasticity', 'Hazard Event', 'Recovery'],
                       right_on=['socio', 'projgroup', 'resil', 'elasticity', 'hazard', 'recovery'], indicator=True)
    logger.debug(("Number of extended scenario snapshots not matched to " +
                  "regression outputs for future year: {}".format(sum(merged2['_merge'] == 'left_only'))))
    if sum(merged2['_merge'] == 'left_only') > 0:
        logger.error(("METAMODEL ERROR: Future year outputs not found for " +
                      "{} scenarios. Re-run metamodel module.".format(sum(merged2['_merge'] == 'left_only'))))
        raise Exception(("METAMODEL ERROR: Future year outputs not found for " +
                         "{} scenarios. Re-run metamodel module.".format(sum(merged2['_merge'] == 'left_only'))))
    merged2.drop(labels=['_merge'], axis=1, inplace=True)

    # merge with base_regression_output in left outer merge on 'Hazard Event' = 'hazard', 'Recovery' = 'recovery'
    # NOTE: merge with base year regression outputs is only based on hazard and recovery
    logger.warning("variation in base year regression outputs is solely due to hazard event and recovery parameters")
    merged2 = pd.merge(merged2, base_regression_output.loc[:, ['hazard', 'recovery', 'trips', 'miles', 'hours']],
                       how='left', left_on=['Hazard Event', 'Recovery'], right_on=['hazard', 'recovery'],
                       suffixes=(None, "_baseyr"), indicator=True)
    logger.debug(("Number of extended scenario snapshots not matched to " +
                  "model outputs for base year: {}".format(sum(merged2['_merge'] == 'left_only'))))
    if sum(merged2['_merge'] == 'left_only') > 0:
        logger.error(("METAMODEL ERROR: Base year outputs not found for " +
                      "{} scenarios".format(sum(merged2['_merge'] == 'left_only'))))
        raise Exception(("METAMODEL ERROR: Base year outputs not found for " +
                         "{} scenarios".format(sum(merged2['_merge'] == 'left_only'))))
    merged2.drop(labels=['hazard_baseyr', 'recovery_baseyr', '_merge'], axis=1, inplace=True)

    # calculate new columns 'initTripslevels'/'initVMTlevels'/'initPHTlevels' as
    # 'trips'/'miles'/'hours' for 'Stage Number' == 1 and 0 otherwise (and dividing by vehicle_occupancy for VMT)
    merged2['initTripslevels'] = np.where(merged2['Stage Number'] == 1, merged2['trips'], 0.0)
    merged2['initVMTlevels'] = np.where(merged2['Stage Number'] == 1, merged2['miles'] / vehicle_occupancy, 0.0)
    merged2['initPHTlevels'] = np.where(merged2['Stage Number'] == 1, merged2['hours'], 0.0)
    merged2['initTripslevels_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['trips_baseyr'], 0.0)
    merged2['initVMTlevels_baseyr'] = np.where(merged2['Stage Number'] == 1,
                                               merged2['miles_baseyr'] / vehicle_occupancy, 0.0)
    merged2['initPHTlevels_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['hours_baseyr'], 0.0)

    # calculate new columns 'expTripslevels'/'expVMTlevels'/'expPHTlevels' by multiplying
    # 'Stage Duration' and 'trips'/'miles'/'hours' (and dividing by vehicle_occupancy for VMT)
    merged2 = merged2.assign(expTripslevels=merged2['Stage Duration'] * merged2['trips'],
                             expVMTlevels=merged2['Stage Duration'] * merged2['miles']/vehicle_occupancy,
                             expPHTlevels=merged2['Stage Duration'] * merged2['hours'])
    merged2 = merged2.assign(expTripslevels_baseyr=merged2['Stage Duration'] * merged2['trips_baseyr'],
                             expVMTlevels_baseyr=merged2['Stage Duration'] * merged2['miles_baseyr']/vehicle_occupancy,
                             expPHTlevels_baseyr=merged2['Stage Duration'] * merged2['hours_baseyr'])

    # create table of maximum recovery stage metrics for partial repair calculation
    # using one row per project-scenario
    logger.debug("identifying maximum recovery stages for partial repair calculation")
    merged2['recovery_depth'] = merged2['Recovery'].astype(float)
    maximum_recovery_data = merged2.loc[merged2.reset_index().groupby(['ID-Resiliency-Scenario'])['recovery_depth'].idxmax(),
                                        ['ID-Resiliency-Scenario', 'trips', 'miles', 'hours',
                                         'trips_baseyr', 'miles_baseyr', 'hours_baseyr']]
    maximum_recovery_data['miles'] = maximum_recovery_data['miles'] / vehicle_occupancy
    maximum_recovery_data['miles_baseyr'] = maximum_recovery_data['miles_baseyr'] / vehicle_occupancy
    maximum_recovery_data.rename({'trips': 'initTripslevels', 'miles': 'initVMTlevels', 'hours': 'initPHTlevels',
                                  'trips_baseyr': 'initTripslevels_baseyr', 'miles_baseyr': 'initVMTlevels_baseyr',
                                  'hours_baseyr': 'initPHTlevels_baseyr'},
                                 axis='columns', inplace=True)

    # consolidate extended scenarios into one row per project-scenario
    # group by 'ID-Resiliency-Scenario', sum metrics columns
    logger.debug("consolidating extended scenario snapshots into uncertainty scenarios")
    hazard_recession_data = merged2.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
                                            'initPHTlevels', 'initTripslevels_baseyr', 'initVMTlevels_baseyr',
                                            'initPHTlevels_baseyr', 'expTripslevels', 'expVMTlevels', 'expPHTlevels',
                                            'expTripslevels_baseyr', 'expVMTlevels_baseyr',
                                            'expPHTlevels_baseyr']].groupby('ID-Resiliency-Scenario', as_index=False,
                                                                            sort=False).sum()

    # calculate dollar values for Trips/VMT/PHT
    logger.debug("calculating dollar values for Trips/VMT/PHT metrics")
    hazard_recession_data = hazard_recession_data.assign(initTripslevel_dollar=(0.5 * vehicle_occupancy *
                                                                                hazard_recession_data['initTripslevels'] *
                                                                                hazard_recession_data['initVMTlevels'] /
                                                                                hazard_recession_data['initPHTlevels']),
                                                         initVMTlevel_dollar=(hazard_recession_data['initVMTlevels'] *
                                                                              miles_cost),
                                                         initPHTlevel_dollar=(hazard_recession_data['initPHTlevels'] *
                                                                              hours_cost),
                                                         expTripslevel_dollar=(0.5 * vehicle_occupancy *
                                                                               hazard_recession_data['expTripslevels'] *
                                                                               hazard_recession_data['expVMTlevels'] /
                                                                               hazard_recession_data['expPHTlevels']),
                                                         expVMTlevel_dollar=(hazard_recession_data['expVMTlevels'] *
                                                                             miles_cost),
                                                         expPHTlevel_dollar=(hazard_recession_data['expPHTlevels'] *
                                                                             hours_cost))
    hazard_recession_data = hazard_recession_data.assign(initTripslevel_dollar_baseyr=(0.5 * vehicle_occupancy *
                                                                                       hazard_recession_data['initTripslevels_baseyr'] *
                                                                                       hazard_recession_data['initVMTlevels_baseyr'] /
                                                                                       hazard_recession_data['initPHTlevels_baseyr']),
                                                         initVMTlevel_dollar_baseyr=(hazard_recession_data['initVMTlevels_baseyr'] *
                                                                                     miles_cost),
                                                         initPHTlevel_dollar_baseyr=(hazard_recession_data['initPHTlevels_baseyr'] *
                                                                                     hours_cost),
                                                         expTripslevel_dollar_baseyr=(0.5 * vehicle_occupancy *
                                                                                      hazard_recession_data['expTripslevels_baseyr'] *
                                                                                      hazard_recession_data['expVMTlevels_baseyr'] /
                                                                                      hazard_recession_data['expPHTlevels_baseyr']),
                                                         expVMTlevel_dollar_baseyr=(hazard_recession_data['expVMTlevels_baseyr'] *
                                                                                    miles_cost),
                                                         expPHTlevel_dollar_baseyr=(hazard_recession_data['expPHTlevels_baseyr'] *
                                                                                    hours_cost))

    # merge with master_table on 'ID-Resiliency-Scenario'
    merged3 = pd.merge(master_table, hazard_recession_data, how='left', on='ID-Resiliency-Scenario', indicator=True)
    logger.debug(("Number of uncertainty scenarios not matched to " +
                  "hazard recession data: {}".format(sum(merged3['_merge'] == 'left_only'))))
    if sum(merged3['_merge'] == 'left_only') == merged3.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with hazard recession data " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with hazard recession data " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged3.drop(labels=['_merge'], axis=1, inplace=True)

    logger.debug("pulling in resilience project and hazard event information")
    # pull in columns for 'Asset', 'Estimated Project Cost', and 'Project Lifespan' from project_list
    merged4 = pd.merge(merged3, project_list.loc[:, ['Project ID', 'Project Name', 'Asset', 'Estimated Project Cost', 'Project Lifespan', 'Estimated Maintenance Cost']],
                       how='left', left_on='Resiliency Project', right_on='Project ID', indicator=True)
    logger.debug(("Number of uncertainty scenarios not matched to " +
                  "resilience project information: {}".format(sum(merged4['_merge'] == 'left_only'))))
    if sum(merged4['_merge'] == 'left_only') == merged4.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with resilience project information " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with resilience project information " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged4.drop(labels=['_merge'], axis=1, inplace=True)
    # create column 'ResiliencyProjectAsset'
    merged4 = merged4.assign(ResiliencyProjectAsset=merged4['Resiliency Project'] + ' - ' + merged4['Asset'])

    # pull in columns for 'HazardDim1', 'HazardDim2', and 'Event Probability' from hazard_levels
    merged5 = pd.merge(merged4, hazard_levels.loc[:, ['Hazard Level', 'HazardDim1', 'HazardDim2', 'Hazard Event',
                                                      'Event Probability in Start Year']],
                       how='left', left_on='Initial Hazard Level', right_on='Hazard Level', indicator=True)
    logger.debug(("Number of uncertainty scenarios not matched to " +
                  "hazard event information: {}".format(sum(merged5['_merge'] == 'left_only'))))
    if sum(merged5['_merge'] == 'left_only') == merged5.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with hazard event information " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with hazard event information " +
                        "failed to produce any matches. Check the corresponding table columns."))
    merged5.drop(labels=['_merge'], axis=1, inplace=True)
    merged5.rename({'Event Probability in Start Year': 'Event Probability'}, axis='columns', inplace=True)
    # create column 'Year'
    merged5['Year'] = str(start_year) + "-" + str(end_year)

    merged5.drop(labels=['Initial Hazard Level', 'Project ID', 'Hazard Level'], axis=1, inplace=True)

    # merge with repair_data in left outer merge on 'ID-Resiliency-Scenario'
    # pull in 'damage_repair', 'total_repair', 'repair_time', and 'damage' for baseline and project scenarios
    logger.debug("pulling in repair cost and time data")
    merged6 = pd.merge(merged5, repair_data.loc[:, ['ID-Resiliency-Scenario', 'baseline_damage_repair',
                                                    'project_damage_repair', 'baseline_total_repair',
                                                    'project_total_repair', 'baseline_repair_time',
                                                    'project_repair_time', 'baseline_damage',
                                                    'project_damage']],
                       how='left', on='ID-Resiliency-Scenario', indicator=True)
    # NOTE: this number will be > 0 for now since baseline scenarios are not found in repair_data table
    logger.debug(("Number of uncertainty scenarios (including baseline scenarios) not matched to " +
                  "damage and repair information: {}".format(sum(merged6['_merge'] == 'left_only'))))
    if sum(merged6['_merge'] == 'left_only') == merged6.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with damage and repair information " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with damage and repair information " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged6.drop(labels=['_merge'], axis=1, inplace=True)

    # create damage and repair cost/time columns across all scenarios
    # NOTE: fields are missing values for baseline scenarios
    merged6['damage_repair'] = np.where(merged6['Resiliency Project'] == 'no', merged6['baseline_damage_repair'],
                                        merged6['project_damage_repair'])
    merged6['total_repair'] = np.where(merged6['Resiliency Project'] == 'no', merged6['baseline_total_repair'],
                                       merged6['project_total_repair'])
    merged6['repair_time'] = np.where(merged6['Resiliency Project'] == 'no', merged6['baseline_repair_time'],
                                      merged6['project_repair_time'])
    merged6['Damage (%)'] = np.where(merged6['Resiliency Project'] == 'no', merged6['baseline_damage'],
                                     merged6['project_damage'])
    merged6.drop(labels=['project_damage_repair', 'project_total_repair', 'project_repair_time', 'project_damage'],
                 axis=1, inplace=True)
    # rename "baseline_" damage and repair measures to "_base"
    merged6.rename({'baseline_damage_repair': 'damage_repair_base', 'baseline_total_repair': 'total_repair_base',
                    'baseline_repair_time': 'repair_time_base', 'baseline_damage': 'damage_base'},
                   axis='columns', inplace=True)

    # use 'ID-Resiliency-Scenario-Baseline' to join to other baseline scenario metrics
    merged7 = pd.merge(merged6, merged6.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
                                                'initPHTlevels', 'initTripslevels_baseyr', 'initVMTlevels_baseyr',
                                                'initPHTlevels_baseyr', 'expTripslevels', 'expVMTlevels',
                                                'expPHTlevels', 'expTripslevels_baseyr', 'expVMTlevels_baseyr',
                                                'expPHTlevels_baseyr']],
                       how='left', left_on='ID-Resiliency-Scenario-Baseline', right_on='ID-Resiliency-Scenario',
                       suffixes=[None, '_base'], indicator=True)
    logger.debug(("Number of uncertainty scenarios not matched to " +
                  "corresponding baseline scenario: {}".format(sum(merged7['_merge'] == 'left_only'))))
    if sum(merged7['_merge'] == 'left_only') == merged7.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with baseline scenario information " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with baseline scenario information " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged7.drop(labels=['_merge'], axis=1, inplace=True)

    # merge with maximum recovery stage metrics for partial repair calculation
    logger.debug("pulling in metrics for maximum recovery stage as proxy for full repaired state")
    merged7 = pd.merge(merged7, maximum_recovery_data, how='left', on='ID-Resiliency-Scenario',
                       suffixes=[None, '_max'], indicator=True)
    logger.debug(("Number of uncertainty scenarios not matched to " +
                  "corresponding maximum recovery stage information: {}".format(sum(merged7['_merge'] == 'left_only'))))
    if sum(merged7['_merge'] == 'left_only') == merged7.shape[0]:
        logger.error(("TABLE JOIN ERROR: Join of uncertainty scenarios with maximum recovery stage information " +
                     "failed to produce any matches. Check the corresponding table columns."))
        raise Exception(("TABLE JOIN ERROR: Join of uncertainty scenarios with maximum recovery stage information " +
                         "failed to produce any matches. Check the corresponding table columns."))
    merged7.drop(labels=['_merge'], axis=1, inplace=True)

    # create column 'DamageRecoveryPath'
    logger.warning("column 'DamageRecoveryPath' assumes linear damage recovery across repair time")
    merged7['DamageRecoveryPath'] = '1,0'
    logger.warning(("columns 'AssetDamagelevels' and 'AssetDamagelevel_dollar' are missing values for baseline scenarios"))
    # create column 'AssetDamagelevels' - set to NaN for baseline scenarios and 'Damage (%)' for resilience project scenarios
    merged7['AssetDamagelevels'] = np.where(merged7['Resiliency Project'] == 'no', np.NaN, merged7['Damage (%)'])
    # create column 'AssetDamagelevel_dollar' - set to NaN for baseline scenarios and 'total_repair' for resilience project scenarios
    merged7['AssetDamagelevel_dollar'] = np.where(merged7['Resiliency Project'] == 'no', np.NaN, merged7['total_repair'])

    # calculate metrics for damage repair period
    # NOTE: fields are missing values for baseline scenarios
    merged7['damTripslevels'] = 0.5 * (merged7['initTripslevels'] + merged7['initTripslevels_max']) * merged7['repair_time']
    merged7['damVMTlevels'] = 0.5 * (merged7['initVMTlevels'] + merged7['initVMTlevels_max']) * merged7['repair_time']
    merged7['damPHTlevels'] = 0.5 * (merged7['initPHTlevels'] + merged7['initPHTlevels_max']) * merged7['repair_time']
    merged7['damTripslevels_baseyr'] = 0.5 * (merged7['initTripslevels_baseyr'] +
                                              merged7['initTripslevels_baseyr_max']) * merged7['repair_time']
    merged7['damVMTlevels_baseyr'] = 0.5 * (merged7['initVMTlevels_baseyr'] +
                                            merged7['initVMTlevels_baseyr_max']) * merged7['repair_time']
    merged7['damPHTlevels_baseyr'] = 0.5 * (merged7['initPHTlevels_baseyr'] +
                                            merged7['initPHTlevels_baseyr_max']) * merged7['repair_time']
    merged7 = merged7.assign(damTripslevel_dollar=(0.5 * vehicle_occupancy * merged7['damTripslevels'] *
                                                   merged7['damVMTlevels'] / merged7['damPHTlevels']),
                             damVMTlevel_dollar=merged7['damVMTlevels'] * miles_cost,
                             damPHTlevel_dollar=merged7['damPHTlevels'] * hours_cost,
                             damTripslevel_dollar_baseyr=(0.5 * vehicle_occupancy * merged7['damTripslevels_baseyr'] *
                                                          merged7['damVMTlevels_baseyr'] /
                                                          merged7['damPHTlevels_baseyr']),
                             damVMTlevel_dollar_baseyr=merged7['damVMTlevels_baseyr'] * miles_cost,
                             damPHTlevel_dollar_baseyr=merged7['damPHTlevels_baseyr'] * hours_cost)

    # calculate vsBase metrics
    # NOTE: calculation is resilience project minus baseline
    merged7['initTripsvsBase'] = merged7['initTripslevels'] - merged7['initTripslevels_base']
    merged7['initVMTvsBase'] = merged7['initVMTlevels'] - merged7['initVMTlevels_base']
    merged7['initPHTvsBase'] = merged7['initPHTlevels'] - merged7['initPHTlevels_base']
    merged7['expTripsvsBase'] = merged7['expTripslevels'] - merged7['expTripslevels_base']
    merged7['expVMTvsBase'] = merged7['expVMTlevels'] - merged7['expVMTlevels_base']
    merged7['expPHTvsBase'] = merged7['expPHTlevels'] - merged7['expPHTlevels_base']
    merged7['damTripsvsBase'] = 0.5 * (merged7['repair_time_base'] *
                                       (merged7['initTripslevels_max'] - merged7['initTripslevels_base']) -
                                       merged7['repair_time'] *
                                       (merged7['initTripslevels_max'] - merged7['initTripslevels']))
    merged7['damVMTvsBase'] = 0.5 * (merged7['repair_time_base'] *
                                     (merged7['initVMTlevels_max'] - merged7['initVMTlevels_base']) -
                                     merged7['repair_time'] *
                                     (merged7['initVMTlevels_max'] - merged7['initVMTlevels']))
    merged7['damPHTvsBase'] = 0.5 * (merged7['repair_time_base'] *
                                     (merged7['initPHTlevels_max'] - merged7['initPHTlevels_base']) -
                                     merged7['repair_time'] *
                                     (merged7['initPHTlevels_max'] - merged7['initPHTlevels']))
    merged7['initTripsvsBase_baseyr'] = merged7['initTripslevels_baseyr'] - merged7['initTripslevels_baseyr_base']
    merged7['initVMTvsBase_baseyr'] = merged7['initVMTlevels_baseyr'] - merged7['initVMTlevels_baseyr_base']
    merged7['initPHTvsBase_baseyr'] = merged7['initPHTlevels_baseyr'] - merged7['initPHTlevels_baseyr_base']
    merged7['expTripsvsBase_baseyr'] = merged7['expTripslevels_baseyr'] - merged7['expTripslevels_baseyr_base']
    merged7['expVMTvsBase_baseyr'] = merged7['expVMTlevels_baseyr'] - merged7['expVMTlevels_baseyr_base']
    merged7['expPHTvsBase_baseyr'] = merged7['expPHTlevels_baseyr'] - merged7['expPHTlevels_baseyr_base']
    merged7['damTripsvsBase_baseyr'] = 0.5 * (merged7['repair_time_base'] *
                                              (merged7['initTripslevels_baseyr_max'] - merged7['initTripslevels_baseyr_base']) -
                                              merged7['repair_time'] *
                                              (merged7['initTripslevels_baseyr_max'] - merged7['initTripslevels_baseyr']))
    merged7['damVMTvsBase_baseyr'] = 0.5 * (merged7['repair_time_base'] *
                                            (merged7['initVMTlevels_baseyr_max'] - merged7['initVMTlevels_baseyr_base']) -
                                            merged7['repair_time'] *
                                            (merged7['initVMTlevels_baseyr_max'] - merged7['initVMTlevels_baseyr']))
    merged7['damPHTvsBase_baseyr'] = 0.5 * (merged7['repair_time_base'] *
                                            (merged7['initPHTlevels_baseyr_max'] - merged7['initPHTlevels_baseyr_base']) -
                                            merged7['repair_time'] *
                                            (merged7['initPHTlevels_baseyr_max'] - merged7['initPHTlevels_baseyr']))
    # calculate dollar values for Trips/VMT/PHT
    merged7 = merged7.assign(initTripsvsBase_dollar=(0.5 * vehicle_occupancy *
                                                     (merged7['initTripsvsBase']) * ((merged7['initVMTlevels_base'] /
                                                                                      merged7['initPHTlevels_base']) -
                                                                                     (merged7['initVMTlevels'] /
                                                                                      merged7['initPHTlevels']))),
                             initVMTvsBase_dollar=merged7['initVMTvsBase'] * miles_cost,
                             initPHTvsBase_dollar=merged7['initPHTvsBase'] * hours_cost,
                             expTripsvsBase_dollar=(0.5 * vehicle_occupancy *
                                                    (merged7['expTripsvsBase']) * ((merged7['expVMTlevels_base'] /
                                                                                    merged7['expPHTlevels_base']) -
                                                                                   (merged7['expVMTlevels'] /
                                                                                    merged7['expPHTlevels']))),
                             expVMTvsBase_dollar=merged7['expVMTvsBase'] * miles_cost,
                             expPHTvsBase_dollar=merged7['expPHTvsBase'] * hours_cost,
                             damTripsvsBase_dollar=(0.5 * vehicle_occupancy *
                                                    (merged7['damTripsvsBase']) * ((merged7['initVMTlevels_base'] /
                                                                                    merged7['initPHTlevels_base']) -
                                                                                   (merged7['initVMTlevels'] /
                                                                                    merged7['initPHTlevels']))),
                             damVMTvsBase_dollar=merged7['damVMTvsBase'] * miles_cost,
                             damPHTvsBase_dollar=merged7['damPHTvsBase'] * hours_cost)
    merged7 = merged7.assign(initTripsvsBase_dollar_baseyr=(0.5 * vehicle_occupancy *
                                                            (merged7['initTripsvsBase_baseyr']) *
                                                            ((merged7['initVMTlevels_baseyr_base'] /
                                                              merged7['initPHTlevels_baseyr_base']) -
                                                             (merged7['initVMTlevels_baseyr'] /
                                                              merged7['initPHTlevels_baseyr']))),
                             initVMTvsBase_dollar_baseyr=merged7['initVMTvsBase_baseyr'] * miles_cost,
                             initPHTvsBase_dollar_baseyr=merged7['initPHTvsBase_baseyr'] * hours_cost,
                             expTripsvsBase_dollar_baseyr=(0.5 * vehicle_occupancy *
                                                           (merged7['expTripsvsBase_baseyr']) *
                                                           ((merged7['expVMTlevels_baseyr_base'] /
                                                             merged7['expPHTlevels_baseyr_base']) -
                                                            (merged7['expVMTlevels_baseyr'] /
                                                             merged7['expPHTlevels_baseyr']))),
                             expVMTvsBase_dollar_baseyr=merged7['expVMTvsBase_baseyr'] * miles_cost,
                             expPHTvsBase_dollar_baseyr=merged7['expPHTvsBase_baseyr'] * hours_cost,
                             damTripsvsBase_dollar_baseyr=(0.5 * vehicle_occupancy *
                                                           (merged7['damTripsvsBase_baseyr']) *
                                                           ((merged7['initVMTlevels_baseyr_base'] /
                                                             merged7['initPHTlevels_baseyr_base']) -
                                                            (merged7['initVMTlevels_baseyr'] /
                                                             merged7['initPHTlevels_baseyr']))),
                             damVMTvsBase_dollar_baseyr=merged7['damVMTvsBase_baseyr'] * miles_cost,
                             damPHTvsBase_dollar_baseyr=merged7['damPHTvsBase_baseyr'] * hours_cost)

    # NOTE: for clean up, set 0 for baseline scenarios to keep NaN from propagating through calculations
    merged7.loc[merged7['Resiliency Project'] == 'no', ['expTripsvsBase_dollar', 'expVMTvsBase_dollar',
                                                        'expPHTvsBase_dollar', 'damTripsvsBase_dollar',
                                                        'damVMTvsBase_dollar', 'damPHTvsBase_dollar',
                                                        'expTripsvsBase_dollar_baseyr', 'expVMTvsBase_dollar_baseyr',
                                                        'expPHTvsBase_dollar_baseyr', 'damTripsvsBase_dollar_baseyr',
                                                        'damVMTvsBase_dollar_baseyr', 'damPHTvsBase_dollar_baseyr',
                                                        'initTripsvsBase_dollar', 'initVMTvsBase_dollar',
                                                        'initPHTvsBase_dollar', 'initTripsvsBase_dollar_baseyr',
                                                        'initVMTvsBase_dollar_baseyr',
                                                        'initPHTvsBase_dollar_baseyr']] = 0
    # create column 'AssetDamagevsBase' - set to 0 for baseline and 'Damage (%)' - 'damage_base' for resiliency scenarios
    # NOTE: for clean up, set 0 for baseline scenarios to keep NaN from propagating through calculations
    merged7['AssetDamagevsBase'] = np.where(merged7['Resiliency Project'] == 'no', 0, merged7['Damage (%)'] - merged7['damage_base'])
    # create column 'AssetDamagevsBase_dollar' - set to 0 for baseline and 'total_repair' - 'total_repair_base' for resiliency scenarios
    # NOTE: for clean up, set 0 for baseline scenarios to keep NaN from propagating through calculations
    merged7['AssetDamagevsBase_dollar'] = np.where(merged7['Resiliency Project'] == 'no', 0,
                                                   merged7['total_repair'] - merged7['total_repair_base'])

    # calculate safety and emissions benefits
    # each benefit is calculated using (1) a config parameter that converts VMT to a safety/emissions metric, (2) a monetization table
    safety_costs = pd.read_csv(safety_monetization_csv, usecols=['Crash Type', 'Monetized Value'],
                               converters={'Crash Type': str, 'Monetized Value': str})
    safety_costs['Monetized Value'] = safety_costs['Monetized Value'].replace('[\$,]', '', regex=True).astype(float)
    fatality_cost = safety_costs[safety_costs['Crash Type'] == 'Fatal']['Monetized Value'].iloc[0]
    injury_cost = safety_costs[safety_costs['Crash Type'] == 'Injury']['Monetized Value'].iloc[0]
    pdo_cost = safety_costs[safety_costs['Crash Type'] == 'PDO']['Monetized Value'].iloc[0]

    # sum of fatality + injury + PDO occurrences * cost (in units of dollars per 100 million vehicle-miles)
    total_safety_cost = (fatality_rate * fatality_cost + injury_rate * injury_cost + pdo_rate * pdo_cost)
    # calculate safety benefits compared to baseline for each period
    merged7['initSafetyvsBase'] =  total_safety_cost * merged7['initVMTvsBase'] / 100000000
    merged7['expSafetyvsBase'] =  total_safety_cost * merged7['expVMTvsBase'] / 100000000
    merged7['damSafetyvsBase'] =  total_safety_cost * merged7['damVMTvsBase'] / 100000000
    merged7['initSafetyvsBase_baseyr'] = total_safety_cost * merged7['initVMTvsBase_baseyr'] / 100000000
    merged7['expSafetyvsBase_baseyr'] = total_safety_cost * merged7['expVMTvsBase_baseyr'] / 100000000
    merged7['damSafetyvsBase_baseyr'] = total_safety_cost * merged7['damVMTvsBase_baseyr'] / 100000000

    # emissions monetization is provided by year (in units of dollars per metric ton)
    emissions_costs = pd.read_csv(emissions_monetization_csv, usecols=['Year', 'NOX', 'SOX', 'PM25', 'CO2'],
                                  converters={'Year': int, 'NOX': str, 'SOX': str, 'PM25': str, 'CO2': str})
    emissions_costs['NOX'] = emissions_costs['NOX'].replace('[\$,]', '', regex=True).astype(float)
    emissions_costs['SOX'] = emissions_costs['SOX'].replace('[\$,]', '', regex=True).astype(float)
    emissions_costs['PM25'] = emissions_costs['PM25'].replace('[\$,]', '', regex=True).astype(float)
    emissions_costs['CO2'] = emissions_costs['CO2'].replace('[\$,]', '', regex=True).astype(float)
    # build out period of analysis series for emissions monetization table
    min_table_year = min(emissions_costs['Year'])
    max_table_year = max(emissions_costs['Year'])
    table_range = (emissions_costs['Year'] >= max(min_table_year, start_year)) & (emissions_costs['Year'] <= min(max_table_year, end_year))
    nox_series = np.concatenate((np.repeat(emissions_costs[emissions_costs['Year'] == min_table_year]['NOX'].iloc[0], max(min_table_year - start_year, 0)),
                                 emissions_costs.loc[table_range, ['NOX']].to_numpy().flatten(),
                                 np.repeat(emissions_costs[emissions_costs['Year'] == max_table_year]['NOX'].iloc[0], max(end_year - max_table_year, 0))))
    so2_series = np.concatenate((np.repeat(emissions_costs[emissions_costs['Year'] == min_table_year]['SOX'].iloc[0], max(min_table_year - start_year, 0)),
                                 emissions_costs.loc[table_range, ['SOX']].to_numpy().flatten(),
                                 np.repeat(emissions_costs[emissions_costs['Year'] == max_table_year]['SOX'].iloc[0], max(end_year - max_table_year, 0))))
    pm25_series = np.concatenate((np.repeat(emissions_costs[emissions_costs['Year'] == min_table_year]['PM25'].iloc[0], max(min_table_year - start_year, 0)),
                                  emissions_costs.loc[table_range, ['PM25']].to_numpy().flatten(),
                                  np.repeat(emissions_costs[emissions_costs['Year'] == max_table_year]['PM25'].iloc[0], max(end_year - max_table_year, 0))))
    co2_series = np.concatenate((np.repeat(emissions_costs[emissions_costs['Year'] == min_table_year]['CO2'].iloc[0], max(min_table_year - start_year, 0)),
                                 emissions_costs.loc[table_range, ['CO2']].to_numpy().flatten(),
                                 np.repeat(emissions_costs[emissions_costs['Year'] == max_table_year]['CO2'].iloc[0], max(end_year - max_table_year, 0))))
    # emissions calculated in for loop to avoid creating too many columns

    logger.debug("interpolating base year and future year runs to calculate metrics across entire analysis period")
    final_table = pd.DataFrame()

    # NOTE: event probability is assumed to be specified for start_year not base_year
    logger.debug("Event Probability assumed to specify probability in start year of period of analysis, not base year")

    for index, row in merged7.iterrows():
        start_frac = (start_year - base_year) / (future_year - base_year)
        end_frac = (end_year - base_year) / (future_year - base_year)

        temp_stage = copy.deepcopy(row)

        initTripslevels_startyr = (row['initTripslevels_baseyr'] +
                                   start_frac * (row['initTripslevels'] - row['initTripslevels_baseyr']))
        initTripslevels_endyr = (row['initTripslevels_baseyr'] +
                                 end_frac * (row['initTripslevels'] - row['initTripslevels_baseyr']))
        initTrips = np.linspace(initTripslevels_startyr, initTripslevels_endyr, end_year - start_year + 1)
        initVMTlevels_startyr = (row['initVMTlevels_baseyr'] +
                                 start_frac * (row['initVMTlevels'] - row['initVMTlevels_baseyr']))
        initVMTlevels_endyr = (row['initVMTlevels_baseyr'] +
                               end_frac * (row['initVMTlevels'] - row['initVMTlevels_baseyr']))
        initVMT = np.linspace(initVMTlevels_startyr, initVMTlevels_endyr, end_year - start_year + 1)
        initPHTlevels_startyr = (row['initPHTlevels_baseyr'] +
                                 start_frac * (row['initPHTlevels'] - row['initPHTlevels_baseyr']))
        initPHTlevels_endyr = (row['initPHTlevels_baseyr'] +
                               end_frac * (row['initPHTlevels'] - row['initPHTlevels_baseyr']))
        initPHT = np.linspace(initPHTlevels_startyr, initPHTlevels_endyr, end_year - start_year + 1)

        temp_stage['initTripslevels'] = np.mean(initTrips)
        temp_stage['initVMTlevels'] = np.mean(initVMT)
        temp_stage['initPHTlevels'] = np.mean(initPHT)

        expTripslevels_startyr = (row['expTripslevels_baseyr'] +
                                  start_frac * (row['expTripslevels'] - row['expTripslevels_baseyr']))
        expTripslevels_endyr = (row['expTripslevels_baseyr'] +
                                end_frac * (row['expTripslevels'] - row['expTripslevels_baseyr']))
        expTrips = np.linspace(expTripslevels_startyr, expTripslevels_endyr, end_year - start_year + 1)
        expVMTlevels_startyr = (row['expVMTlevels_baseyr'] +
                                start_frac * (row['expVMTlevels'] - row['expVMTlevels_baseyr']))
        expVMTlevels_endyr = (row['expVMTlevels_baseyr'] +
                              end_frac * (row['expVMTlevels'] - row['expVMTlevels_baseyr']))
        expVMT = np.linspace(expVMTlevels_startyr, expVMTlevels_endyr, end_year - start_year + 1)
        expPHTlevels_startyr = (row['expPHTlevels_baseyr'] +
                                start_frac * (row['expPHTlevels'] - row['expPHTlevels_baseyr']))
        expPHTlevels_endyr = (row['expPHTlevels_baseyr'] +
                              end_frac * (row['expPHTlevels'] - row['expPHTlevels_baseyr']))
        expPHT = np.linspace(expPHTlevels_startyr, expPHTlevels_endyr, end_year - start_year + 1)

        temp_stage['expTripslevels'] = np.mean(expTrips)
        temp_stage['expVMTlevels'] = np.mean(expVMT)
        temp_stage['expPHTlevels'] = np.mean(expPHT)

        damTripslevels_startyr = (row['damTripslevels_baseyr'] +
                                  start_frac * (row['damTripslevels'] - row['damTripslevels_baseyr']))
        damTripslevels_endyr = (row['damTripslevels_baseyr'] +
                                end_frac * (row['damTripslevels'] - row['damTripslevels_baseyr']))
        damTrips = np.linspace(damTripslevels_startyr, damTripslevels_endyr, end_year - start_year + 1)
        damVMTlevels_startyr = (row['damVMTlevels_baseyr'] +
                                start_frac * (row['damVMTlevels'] - row['damVMTlevels_baseyr']))
        damVMTlevels_endyr = (row['damVMTlevels_baseyr'] +
                              end_frac * (row['damVMTlevels'] - row['damVMTlevels_baseyr']))
        damVMT = np.linspace(damVMTlevels_startyr, damVMTlevels_endyr, end_year - start_year + 1)
        damPHTlevels_startyr = (row['damPHTlevels_baseyr'] +
                                start_frac * (row['damPHTlevels'] - row['damPHTlevels_baseyr']))
        damPHTlevels_endyr = (row['damPHTlevels_baseyr'] +
                              end_frac * (row['damPHTlevels'] - row['damPHTlevels_baseyr']))
        damPHT = np.linspace(damPHTlevels_startyr, damPHTlevels_endyr, end_year - start_year + 1)

        temp_stage['damTripslevels'] = np.mean(damTrips)
        temp_stage['damVMTlevels'] = np.mean(damVMT)
        temp_stage['damPHTlevels'] = np.mean(damPHT)

        initTripslevel_dollar_startyr = (row['initTripslevel_dollar_baseyr'] +
                                         start_frac *
                                         (row['initTripslevel_dollar'] - row['initTripslevel_dollar_baseyr']))
        initTripslevel_dollar_endyr = (row['initTripslevel_dollar_baseyr'] +
                                       end_frac *
                                       (row['initTripslevel_dollar'] - row['initTripslevel_dollar_baseyr']))
        initTrips_dollar = np.linspace(initTripslevel_dollar_startyr, initTripslevel_dollar_endyr,
                                       end_year - start_year + 1)
        initVMTlevel_dollar_startyr = (row['initVMTlevel_dollar_baseyr'] +
                                       start_frac *
                                       (row['initVMTlevel_dollar'] - row['initVMTlevel_dollar_baseyr']))
        initVMTlevel_dollar_endyr = (row['initVMTlevel_dollar_baseyr'] +
                                     end_frac *
                                     (row['initVMTlevel_dollar'] - row['initVMTlevel_dollar_baseyr']))
        initVMT_dollar = np.linspace(initVMTlevel_dollar_startyr, initVMTlevel_dollar_endyr, end_year - start_year + 1)
        initPHTlevel_dollar_startyr = (row['initPHTlevel_dollar_baseyr'] +
                                       start_frac *
                                       (row['initPHTlevel_dollar'] - row['initPHTlevel_dollar_baseyr']))
        initPHTlevel_dollar_endyr = (row['initPHTlevel_dollar_baseyr'] +
                                     end_frac *
                                     (row['initPHTlevel_dollar'] - row['initPHTlevel_dollar_baseyr']))
        initPHT_dollar = np.linspace(initPHTlevel_dollar_startyr, initPHTlevel_dollar_endyr, end_year - start_year + 1)

        temp_stage['initTripslevel_dollar'] = np.mean(initTrips_dollar)
        temp_stage['initVMTlevel_dollar'] = np.mean(initVMT_dollar)
        temp_stage['initPHTlevel_dollar'] = np.mean(initPHT_dollar)

        expTripslevel_dollar_startyr = (row['expTripslevel_dollar_baseyr'] +
                                        start_frac * (row['expTripslevel_dollar'] - row['expTripslevel_dollar_baseyr']))
        expTripslevel_dollar_endyr = (row['expTripslevel_dollar_baseyr'] +
                                      end_frac * (row['expTripslevel_dollar'] - row['expTripslevel_dollar_baseyr']))
        expTrips_dollar = np.linspace(expTripslevel_dollar_startyr, expTripslevel_dollar_endyr,
                                      end_year - start_year + 1)
        expVMTlevel_dollar_startyr = (row['expVMTlevel_dollar_baseyr'] +
                                      start_frac * (row['expVMTlevel_dollar'] - row['expVMTlevel_dollar_baseyr']))
        expVMTlevel_dollar_endyr = (row['expVMTlevel_dollar_baseyr'] +
                                    end_frac * (row['expVMTlevel_dollar'] - row['expVMTlevel_dollar_baseyr']))
        expVMT_dollar = np.linspace(expVMTlevel_dollar_startyr, expVMTlevel_dollar_endyr, end_year - start_year + 1)
        expPHTlevel_dollar_startyr = (row['expPHTlevel_dollar_baseyr'] +
                                      start_frac * (row['expPHTlevel_dollar'] - row['expPHTlevel_dollar_baseyr']))
        expPHTlevel_dollar_endyr = (row['expPHTlevel_dollar_baseyr'] +
                                    end_frac * (row['expPHTlevel_dollar'] - row['expPHTlevel_dollar_baseyr']))
        expPHT_dollar = np.linspace(expPHTlevel_dollar_startyr, expPHTlevel_dollar_endyr, end_year - start_year + 1)

        temp_stage['expTripslevel_dollar'] = np.mean(expTrips_dollar)
        temp_stage['expVMTlevel_dollar'] = np.mean(expVMT_dollar)
        temp_stage['expPHTlevel_dollar'] = np.mean(expPHT_dollar)

        damTripslevel_dollar_startyr = (row['damTripslevel_dollar_baseyr'] +
                                        start_frac * (row['damTripslevel_dollar'] - row['damTripslevel_dollar_baseyr']))
        damTripslevel_dollar_endyr = (row['damTripslevel_dollar_baseyr'] +
                                      end_frac * (row['damTripslevel_dollar'] - row['damTripslevel_dollar_baseyr']))
        damTrips_dollar = np.linspace(damTripslevel_dollar_startyr, damTripslevel_dollar_endyr,
                                      end_year - start_year + 1)
        damVMTlevel_dollar_startyr = (row['damVMTlevel_dollar_baseyr'] +
                                      start_frac * (row['damVMTlevel_dollar'] - row['damVMTlevel_dollar_baseyr']))
        damVMTlevel_dollar_endyr = (row['damVMTlevel_dollar_baseyr'] +
                                    end_frac * (row['damVMTlevel_dollar'] - row['damVMTlevel_dollar_baseyr']))
        damVMT_dollar = np.linspace(damVMTlevel_dollar_startyr, damVMTlevel_dollar_endyr, end_year - start_year + 1)
        damPHTlevel_dollar_startyr = (row['damPHTlevel_dollar_baseyr'] +
                                      start_frac * (row['damPHTlevel_dollar'] - row['damPHTlevel_dollar_baseyr']))
        damPHTlevel_dollar_endyr = (row['damPHTlevel_dollar_baseyr'] +
                                    end_frac * (row['damPHTlevel_dollar'] - row['damPHTlevel_dollar_baseyr']))
        damPHT_dollar = np.linspace(damPHTlevel_dollar_startyr, damPHTlevel_dollar_endyr, end_year - start_year + 1)

        temp_stage['damTripslevel_dollar'] = np.mean(damTrips_dollar)
        temp_stage['damVMTlevel_dollar'] = np.mean(damVMT_dollar)
        temp_stage['damPHTlevel_dollar'] = np.mean(damPHT_dollar)

        initTripsvsBase_startyr = (row['initTripsvsBase_baseyr'] +
                                   start_frac * (row['initTripsvsBase'] - row['initTripsvsBase_baseyr']))
        initTripsvsBase_endyr = (row['initTripsvsBase_baseyr'] +
                                 end_frac * (row['initTripsvsBase'] - row['initTripsvsBase_baseyr']))
        initTripsvsBase = np.linspace(initTripsvsBase_startyr, initTripsvsBase_endyr, end_year - start_year + 1)
        initVMTvsBase_startyr = (row['initVMTvsBase_baseyr'] +
                                 start_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr']))
        initVMTvsBase_endyr = (row['initVMTvsBase_baseyr'] +
                               end_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr']))
        initVMTvsBase = np.linspace(initVMTvsBase_startyr, initVMTvsBase_endyr, end_year - start_year + 1)
        initPHTvsBase_startyr = (row['initPHTvsBase_baseyr'] +
                                 start_frac * (row['initPHTvsBase'] - row['initPHTvsBase_baseyr']))
        initPHTvsBase_endyr = (row['initPHTvsBase_baseyr'] +
                               end_frac * (row['initPHTvsBase'] - row['initPHTvsBase_baseyr']))
        initPHTvsBase = np.linspace(initPHTvsBase_startyr, initPHTvsBase_endyr, end_year - start_year + 1)

        temp_stage['initTripsvsBase'] = np.mean(initTripsvsBase)
        temp_stage['initVMTvsBase'] = np.mean(initVMTvsBase)
        temp_stage['initPHTvsBase'] = np.mean(initPHTvsBase)

        initTripsvsBase_dollar_startyr = (row['initTripsvsBase_dollar_baseyr'] +
                                          start_frac *
                                          (row['initTripsvsBase_dollar'] - row['initTripsvsBase_dollar_baseyr']))
        initTripsvsBase_dollar_endyr = (row['initTripsvsBase_dollar_baseyr'] +
                                        end_frac *
                                        (row['initTripsvsBase_dollar'] - row['initTripsvsBase_dollar_baseyr']))
        initTripsvsBase_dollar = np.linspace(initTripsvsBase_dollar_startyr, initTripsvsBase_dollar_endyr,
                                             end_year - start_year + 1)
        initVMTvsBase_dollar_startyr = (row['initVMTvsBase_dollar_baseyr'] +
                                        start_frac * (row['initVMTvsBase_dollar'] - row['initVMTvsBase_dollar_baseyr']))
        initVMTvsBase_dollar_endyr = (row['initVMTvsBase_dollar_baseyr'] +
                                      end_frac * (row['initVMTvsBase_dollar'] - row['initVMTvsBase_dollar_baseyr']))
        initVMTvsBase_dollar = np.linspace(initVMTvsBase_dollar_startyr, initVMTvsBase_dollar_endyr,
                                           end_year - start_year + 1)
        initPHTvsBase_dollar_startyr = (row['initPHTvsBase_dollar_baseyr'] +
                                        start_frac * (row['initPHTvsBase_dollar'] - row['initPHTvsBase_dollar_baseyr']))
        initPHTvsBase_dollar_endyr = (row['initPHTvsBase_dollar_baseyr'] +
                                      end_frac * (row['initPHTvsBase_dollar'] - row['initPHTvsBase_dollar_baseyr']))
        initPHTvsBase_dollar = np.linspace(initPHTvsBase_dollar_startyr, initPHTvsBase_dollar_endyr,
                                           end_year - start_year + 1)

        temp_stage['initTripsvsBase_dollar'] = np.mean(initTripsvsBase_dollar)
        temp_stage['initVMTvsBase_dollar'] = np.mean(initVMTvsBase_dollar)
        temp_stage['initPHTvsBase_dollar'] = np.mean(initPHTvsBase_dollar)

        expTripsvsBase_startyr = (row['expTripsvsBase_baseyr'] +
                                  start_frac * (row['expTripsvsBase'] - row['expTripsvsBase_baseyr']))
        expTripsvsBase_endyr = (row['expTripsvsBase_baseyr'] +
                                end_frac * (row['expTripsvsBase'] - row['expTripsvsBase_baseyr']))
        expTripsvsBase = np.linspace(expTripsvsBase_startyr, expTripsvsBase_endyr, end_year - start_year + 1)
        expVMTvsBase_startyr = (row['expVMTvsBase_baseyr'] +
                                start_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr']))
        expVMTvsBase_endyr = row['expVMTvsBase_baseyr'] + end_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr'])
        expVMTvsBase = np.linspace(expVMTvsBase_startyr, expVMTvsBase_endyr, end_year - start_year + 1)
        expPHTvsBase_startyr = (row['expPHTvsBase_baseyr'] +
                                start_frac * (row['expPHTvsBase'] - row['expPHTvsBase_baseyr']))
        expPHTvsBase_endyr = row['expPHTvsBase_baseyr'] + end_frac * (row['expPHTvsBase'] - row['expPHTvsBase_baseyr'])
        expPHTvsBase = np.linspace(expPHTvsBase_startyr, expPHTvsBase_endyr, end_year - start_year + 1)

        temp_stage['expTripsvsBase'] = np.mean(expTripsvsBase)
        temp_stage['expVMTvsBase'] = np.mean(expVMTvsBase)
        temp_stage['expPHTvsBase'] = np.mean(expPHTvsBase)

        expTripsvsBase_dollar_startyr = (row['expTripsvsBase_dollar_baseyr'] +
                                         start_frac *
                                         (row['expTripsvsBase_dollar'] - row['expTripsvsBase_dollar_baseyr']))
        expTripsvsBase_dollar_endyr = (row['expTripsvsBase_dollar_baseyr'] +
                                       end_frac * (row['expTripsvsBase_dollar'] - row['expTripsvsBase_dollar_baseyr']))
        expTripsvsBase_dollar = np.linspace(expTripsvsBase_dollar_startyr, expTripsvsBase_dollar_endyr,
                                            end_year - start_year + 1)
        expVMTvsBase_dollar_startyr = (row['expVMTvsBase_dollar_baseyr'] +
                                       start_frac * (row['expVMTvsBase_dollar'] - row['expVMTvsBase_dollar_baseyr']))
        expVMTvsBase_dollar_endyr = (row['expVMTvsBase_dollar_baseyr'] +
                                     end_frac * (row['expVMTvsBase_dollar'] - row['expVMTvsBase_dollar_baseyr']))
        expVMTvsBase_dollar = np.linspace(expVMTvsBase_dollar_startyr, expVMTvsBase_dollar_endyr,
                                          end_year - start_year + 1)
        expPHTvsBase_dollar_startyr = (row['expPHTvsBase_dollar_baseyr'] +
                                       start_frac * (row['expPHTvsBase_dollar'] - row['expPHTvsBase_dollar_baseyr']))
        expPHTvsBase_dollar_endyr = (row['expPHTvsBase_dollar_baseyr'] +
                                     end_frac * (row['expPHTvsBase_dollar'] - row['expPHTvsBase_dollar_baseyr']))
        expPHTvsBase_dollar = np.linspace(expPHTvsBase_dollar_startyr, expPHTvsBase_dollar_endyr,
                                          end_year - start_year + 1)

        temp_stage['expTripsvsBase_dollar'] = np.mean(expTripsvsBase_dollar)
        temp_stage['expVMTvsBase_dollar'] = np.mean(expVMTvsBase_dollar)
        temp_stage['expPHTvsBase_dollar'] = np.mean(expPHTvsBase_dollar)

        damTripsvsBase_startyr = (row['damTripsvsBase_baseyr'] +
                                  start_frac * (row['damTripsvsBase'] - row['damTripsvsBase_baseyr']))
        damTripsvsBase_endyr = (row['damTripsvsBase_baseyr'] +
                                end_frac * (row['damTripsvsBase'] - row['damTripsvsBase_baseyr']))
        damTripsvsBase = np.linspace(damTripsvsBase_startyr, damTripsvsBase_endyr, end_year - start_year + 1)
        damVMTvsBase_startyr = (row['damVMTvsBase_baseyr'] +
                                start_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr']))
        damVMTvsBase_endyr = row['damVMTvsBase_baseyr'] + end_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr'])
        damVMTvsBase = np.linspace(damVMTvsBase_startyr, damVMTvsBase_endyr, end_year - start_year + 1)
        damPHTvsBase_startyr = (row['damPHTvsBase_baseyr'] +
                                start_frac * (row['damPHTvsBase'] - row['damPHTvsBase_baseyr']))
        damPHTvsBase_endyr = row['damPHTvsBase_baseyr'] + end_frac * (row['damPHTvsBase'] - row['damPHTvsBase_baseyr'])
        damPHTvsBase = np.linspace(damPHTvsBase_startyr, damPHTvsBase_endyr, end_year - start_year + 1)

        temp_stage['damTripsvsBase'] = np.mean(damTripsvsBase)
        temp_stage['damVMTvsBase'] = np.mean(damVMTvsBase)
        temp_stage['damPHTvsBase'] = np.mean(damPHTvsBase)

        damTripsvsBase_dollar_startyr = (row['damTripsvsBase_dollar_baseyr'] +
                                         start_frac *
                                         (row['damTripsvsBase_dollar'] - row['damTripsvsBase_dollar_baseyr']))
        damTripsvsBase_dollar_endyr = (row['damTripsvsBase_dollar_baseyr'] +
                                       end_frac * (row['damTripsvsBase_dollar'] - row['damTripsvsBase_dollar_baseyr']))
        damTripsvsBase_dollar = np.linspace(damTripsvsBase_dollar_startyr, damTripsvsBase_dollar_endyr,
                                            end_year - start_year + 1)
        damVMTvsBase_dollar_startyr = (row['damVMTvsBase_dollar_baseyr'] +
                                       start_frac * (row['damVMTvsBase_dollar'] - row['damVMTvsBase_dollar_baseyr']))
        damVMTvsBase_dollar_endyr = (row['damVMTvsBase_dollar_baseyr'] +
                                     end_frac * (row['damVMTvsBase_dollar'] - row['damVMTvsBase_dollar_baseyr']))
        damVMTvsBase_dollar = np.linspace(damVMTvsBase_dollar_startyr, damVMTvsBase_dollar_endyr,
                                          end_year - start_year + 1)
        damPHTvsBase_dollar_startyr = (row['damPHTvsBase_dollar_baseyr'] +
                                       start_frac * (row['damPHTvsBase_dollar'] - row['damPHTvsBase_dollar_baseyr']))
        damPHTvsBase_dollar_endyr = (row['damPHTvsBase_dollar_baseyr'] +
                                     end_frac * (row['damPHTvsBase_dollar'] - row['damPHTvsBase_dollar_baseyr']))
        damPHTvsBase_dollar = np.linspace(damPHTvsBase_dollar_startyr, damPHTvsBase_dollar_endyr,
                                          end_year - start_year + 1)

        temp_stage['damTripsvsBase_dollar'] = np.mean(damTripsvsBase_dollar)
        temp_stage['damVMTvsBase_dollar'] = np.mean(damVMTvsBase_dollar)
        temp_stage['damPHTvsBase_dollar'] = np.mean(damPHTvsBase_dollar)

        # incorporate event frequency factor into 'Event Probability' column
        event_prob = np.zeros((end_year - start_year + 1,))
        event_prob[0] = row['Event Probability']
        event_prob[1:] = row['Future Event Frequency']
        event_prob = np.cumprod(event_prob)
        discount = np.zeros((end_year - start_year + 1,))
        discount[0] = np.float_power(1 + discount_factor, start_year - dollar_year)
        discount[1:] = 1 + discount_factor
        discount = np.cumprod(discount)

        # safety calculations
        initSafetyvsBase_startyr = (row['initSafetyvsBase_baseyr'] +
                                    start_frac * (row['initSafetyvsBase'] - row['initSafetyvsBase_baseyr']))
        initSafetyvsBase_endyr = (row['initSafetyvsBase_baseyr'] +
                                  end_frac * (row['initSafetyvsBase'] - row['initSafetyvsBase_baseyr']))
        initSafetyvsBase = np.linspace(initSafetyvsBase_startyr, initSafetyvsBase_endyr, end_year - start_year + 1)
        expSafetyvsBase_startyr = (row['expSafetyvsBase_baseyr'] +
                                   start_frac * (row['expSafetyvsBase'] - row['expSafetyvsBase_baseyr']))
        expSafetyvsBase_endyr = (row['expSafetyvsBase_baseyr'] +
                                 end_frac * (row['expSafetyvsBase'] - row['expSafetyvsBase_baseyr']))
        expSafetyvsBase = np.linspace(expSafetyvsBase_startyr, expSafetyvsBase_endyr, end_year - start_year + 1)
        damSafetyvsBase_startyr = (row['damSafetyvsBase_baseyr'] +
                                   start_frac * (row['damSafetyvsBase'] - row['damSafetyvsBase_baseyr']))
        damSafetyvsBase_endyr = (row['damSafetyvsBase_baseyr'] +
                                 end_frac * (row['damSafetyvsBase'] - row['damSafetyvsBase_baseyr']))
        damSafetyvsBase = np.linspace(damSafetyvsBase_startyr, damSafetyvsBase_endyr, end_year - start_year + 1)

        temp_stage['initSafetyvsBase'] = np.mean(initSafetyvsBase)
        temp_stage['expSafetyvsBase'] = np.mean(expSafetyvsBase)
        temp_stage['damSafetyvsBase'] = np.mean(damSafetyvsBase)
        temp_stage['initSafety_Discounted'] = np.sum(initSafetyvsBase / discount)
        temp_stage['expSafety_Discounted'] = np.sum(expSafetyvsBase / discount)
        temp_stage['damSafety_Discounted'] = np.sum(damSafetyvsBase / discount)

        # emissions calculations (in metric tons)
        initNOXvsBase_startyr = (row['initVMTvsBase_baseyr'] +
                                 start_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr'])) * nox_rate / 1000000
        initNOXvsBase_endyr = (row['initVMTvsBase_baseyr'] +
                               end_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr'])) * nox_rate / 1000000
        initNOXvsBase = np.linspace(initNOXvsBase_startyr, initNOXvsBase_endyr, end_year - start_year + 1)
        initSO2vsBase_startyr = (row['initVMTvsBase_baseyr'] +
                                 start_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr'])) * so2_rate / 1000000
        initSO2vsBase_endyr = (row['initVMTvsBase_baseyr'] +
                               end_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr'])) * so2_rate / 1000000
        initSO2vsBase = np.linspace(initSO2vsBase_startyr, initSO2vsBase_endyr, end_year - start_year + 1)
        initPM25vsBase_startyr = (row['initVMTvsBase_baseyr'] +
                                  start_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr'])) * pm25_rate / 1000000
        initPM25vsBase_endyr = (row['initVMTvsBase_baseyr'] +
                                end_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr'])) * pm25_rate / 1000000
        initPM25vsBase = np.linspace(initPM25vsBase_startyr, initPM25vsBase_endyr, end_year - start_year + 1)
        initCO2vsBase_startyr = (row['initVMTvsBase_baseyr'] +
                                 start_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr'])) * co2_rate / 1000000
        initCO2vsBase_endyr = (row['initVMTvsBase_baseyr'] +
                               end_frac * (row['initVMTvsBase'] - row['initVMTvsBase_baseyr'])) * co2_rate / 1000000
        initCO2vsBase = np.linspace(initCO2vsBase_startyr, initCO2vsBase_endyr, end_year - start_year + 1)
        # emissions monetization (using dollars per metric ton)
        initEmissionsvsBase = initNOXvsBase * nox_series + initSO2vsBase * so2_series + initPM25vsBase * pm25_series + initCO2vsBase * co2_series

        expNOXvsBase_startyr = (row['expVMTvsBase_baseyr'] +
                                start_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr'])) * nox_rate / 1000000
        expNOXvsBase_endyr = (row['expVMTvsBase_baseyr'] +
                              end_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr'])) * nox_rate / 1000000
        expNOXvsBase = np.linspace(expNOXvsBase_startyr, expNOXvsBase_endyr, end_year - start_year + 1)
        expSO2vsBase_startyr = (row['expVMTvsBase_baseyr'] +
                                start_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr'])) * so2_rate / 1000000
        expSO2vsBase_endyr = (row['expVMTvsBase_baseyr'] +
                              end_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr'])) * so2_rate / 1000000
        expSO2vsBase = np.linspace(expSO2vsBase_startyr, expSO2vsBase_endyr, end_year - start_year + 1)
        expPM25vsBase_startyr = (row['expVMTvsBase_baseyr'] +
                                 start_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr'])) * pm25_rate / 1000000
        expPM25vsBase_endyr = (row['expVMTvsBase_baseyr'] +
                               end_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr'])) * pm25_rate / 1000000
        expPM25vsBase = np.linspace(expPM25vsBase_startyr, expPM25vsBase_endyr, end_year - start_year + 1)
        expCO2vsBase_startyr = (row['expVMTvsBase_baseyr'] +
                                start_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr'])) * co2_rate / 1000000
        expCO2vsBase_endyr = (row['expVMTvsBase_baseyr'] +
                              end_frac * (row['expVMTvsBase'] - row['expVMTvsBase_baseyr'])) * co2_rate / 1000000
        expCO2vsBase = np.linspace(expCO2vsBase_startyr, expCO2vsBase_endyr, end_year - start_year + 1)
        # emissions monetization (using dollars per metric ton)
        expEmissionsvsBase = expNOXvsBase * nox_series + expSO2vsBase * so2_series + expPM25vsBase * pm25_series + expCO2vsBase * co2_series

        damNOXvsBase_startyr = (row['damVMTvsBase_baseyr'] +
                                start_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr'])) * nox_rate / 1000000
        damNOXvsBase_endyr = (row['damVMTvsBase_baseyr'] +
                              end_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr'])) * nox_rate / 1000000
        damNOXvsBase = np.linspace(damNOXvsBase_startyr, damNOXvsBase_endyr, end_year - start_year + 1)
        damSO2vsBase_startyr = (row['damVMTvsBase_baseyr'] +
                                start_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr'])) * so2_rate / 1000000
        damSO2vsBase_endyr = (row['damVMTvsBase_baseyr'] +
                              end_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr'])) * so2_rate / 1000000
        damSO2vsBase = np.linspace(damSO2vsBase_startyr, damSO2vsBase_endyr, end_year - start_year + 1)
        damPM25vsBase_startyr = (row['damVMTvsBase_baseyr'] +
                                 start_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr'])) * pm25_rate / 1000000
        damPM25vsBase_endyr = (row['damVMTvsBase_baseyr'] +
                               end_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr'])) * pm25_rate / 1000000
        damPM25vsBase = np.linspace(damPM25vsBase_startyr, damPM25vsBase_endyr, end_year - start_year + 1)
        damCO2vsBase_startyr = (row['damVMTvsBase_baseyr'] +
                                start_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr'])) * co2_rate / 1000000
        damCO2vsBase_endyr = (row['damVMTvsBase_baseyr'] +
                              end_frac * (row['damVMTvsBase'] - row['damVMTvsBase_baseyr'])) * co2_rate / 1000000
        damCO2vsBase = np.linspace(damCO2vsBase_startyr, damCO2vsBase_endyr, end_year - start_year + 1)
        # emissions monetization (using dollars per metric ton)
        damEmissionsvsBase = damNOXvsBase * nox_series + damSO2vsBase * so2_series + damPM25vsBase * pm25_series + damCO2vsBase * co2_series

        temp_stage['initEmissionsvsBase'] = np.mean(initEmissionsvsBase)
        temp_stage['expEmissionsvsBase'] = np.mean(expEmissionsvsBase)
        temp_stage['damEmissionsvsBase'] = np.mean(damEmissionsvsBase)

        temp_stage['initEmissions_Discounted'] = np.sum(initEmissionsvsBase / discount)
        temp_stage['expEmissions_Discounted'] = np.sum(expEmissionsvsBase / discount)
        temp_stage['damEmissions_Discounted'] = np.sum(damEmissionsvsBase / discount)

        # calculate (1) discounted maintenance cost, (2) discounted project cost based on lifespan, (3) residual cost benefit
        cost_stream = np.zeros((end_year - start_year + 1,))
        cost_stream[::row['Project Lifespan']] = row['Estimated Project Cost']
        temp_stage['ProjectCosts_Discounted'] = np.sum(cost_stream / discount)
        residual_stream = np.zeros((end_year - start_year + 1,))
        remaining_years = row['Project Lifespan'] - (end_year - start_year + 1) % row['Project Lifespan']
        residual_stream[-1] = row['Estimated Project Cost'] * (remaining_years / row['Project Lifespan'])
        temp_stage['TotalResidual_Discounted'] = np.sum(residual_stream / discount)
        maintenance_stream = np.repeat(row['Estimated Maintenance Cost'], end_year - start_year + 1)
        temp_stage['TotalMaintenanceCosts_Discounted'] = np.sum(maintenance_stream / discount)

        if roi_analysis_type == 'Breakeven':
            temp_stage['ProjectCosts_Discounted'] = 0
            temp_stage['TotalResidual_Discounted'] = 0
            temp_stage['TotalMaintenanceCosts_Discounted'] = 0

        temp_stage['Benefits_Discounted'] = np.sum((expTripsvsBase_dollar + expVMTvsBase_dollar + expPHTvsBase_dollar
                                                    - row['AssetDamagevsBase_dollar'] + damTripsvsBase_dollar
                                                    + damVMTvsBase_dollar + damPHTvsBase_dollar)
                                                   * event_prob / discount) + temp_stage['TotalResidual_Discounted'] - temp_stage['TotalMaintenanceCosts_Discounted']
        temp_stage['ExpBenefits_Discounted'] = np.sum((expTripsvsBase_dollar + expVMTvsBase_dollar
                                                       + expPHTvsBase_dollar) * event_prob / discount)
        temp_stage['RepairCleanupCostSavings_Discounted'] = np.sum((0 - row['AssetDamagevsBase_dollar']) *
                                                                   event_prob / discount)
        temp_stage['DamBenefits_Discounted'] = np.sum((damTripsvsBase_dollar + damVMTvsBase_dollar
                                                       + damPHTvsBase_dollar) * event_prob / discount)
        temp_stage['NetBenefits_Discounted'] = temp_stage['Benefits_Discounted'] - temp_stage['ProjectCosts_Discounted']
        if temp_stage['ProjectCosts_Discounted'] == 0:
            temp_stage['BCR_Discounted'] = np.NaN
        else:
            temp_stage['BCR_Discounted'] = np.float64(temp_stage['Benefits_Discounted']) / temp_stage['ProjectCosts_Discounted']

        final_table = final_table.append(temp_stage, ignore_index=True)

    # column for BCA rolled up across hazard events for each uncertainty scenario (no hazard)
    # and project group + resiliency project combination
    logger.debug(("calculating total BCA for each uncertainty scenario and " +
                  "project group + resiliency project combination across types of hazard events"))
    # average BCA across hazard recession lengths for each hazard event, assuming equal probability of recession length
    BCArecov = final_table.loc[:, ['Resiliency Project', 'Project Group', 'IDScenarioNoHazard', 'Hazard Event',
                                   'Benefits_Discounted']].groupby(['Resiliency Project', 'Project Group',
                                                                    'IDScenarioNoHazard', 'Hazard Event'],
                                                                   as_index=False, sort=False).mean()
    # sum BCA across hazard events, with event probability already factored into BCA calculation
    BCAnohazard = BCArecov.groupby(['Resiliency Project', 'Project Group', 'IDScenarioNoHazard'],
                                   as_index=False, sort=False).sum()
    BCAnohazard.rename({'Benefits_Discounted': 'TotalNetBenefits_Discounted'}, axis='columns', inplace=True)
    final_table = pd.merge(final_table, BCAnohazard, how='left',
                           on=['Resiliency Project', 'Project Group', 'IDScenarioNoHazard'])
    final_table['TotalNetBenefits_Discounted'] = (final_table['TotalNetBenefits_Discounted'] -
                                                  final_table['ProjectCosts_Discounted'])

    # create column 'RegretAll' as ranking of 'NetBenefits_Discounted'
    # for resiliency projects averaged across all uncertainty scenarios
    # average is to equally weight 'no' Resiliency Project baseline case across project groups
    # with other Resiliency Project cases
    # NOTE: use average across baseline scenarios as the baseline scenario counted in the Tableau summary dashboard
    logger.debug("calculating regret metrics")
    BCAmean = final_table.loc[:, ['Resiliency Project', 'NetBenefits_Discounted']].groupby('Resiliency Project',
                                                                                           as_index=False,
                                                                                           sort=False).mean()
    BCAmean['RegretAll'] = BCAmean['NetBenefits_Discounted'].rank(method='dense', ascending=False)
    final_table = pd.merge(final_table, BCAmean.loc[:, ['Resiliency Project', 'RegretAll']],
                           how='left', on='Resiliency Project')
    # create column 'RegretScenario' as ranking of 'NetBenefits_Discounted'
    # for resiliency projects grouped by uncertainty scenario (across project groups)
    BCAbyScenario = final_table.loc[:, ['ID-Uncertainty Scenario', 'Resiliency Project',
                                        'NetBenefits_Discounted']].groupby(['ID-Uncertainty Scenario',
                                                                            'Resiliency Project'],
                                                                           as_index=False, sort=False).mean()
    BCAbyScenario['RegretScenario'] = BCAbyScenario.groupby('ID-Uncertainty Scenario')['NetBenefits_Discounted'].rank(
        method='dense', ascending=False)
    final_table = pd.merge(final_table, BCAbyScenario.loc[:, ['ID-Uncertainty Scenario', 'Resiliency Project',
                                                              'RegretScenario']],
                           how='left', on=['ID-Uncertainty Scenario', 'Resiliency Project'])
    # create column 'RegretAsset' as ranking of 'NetBenefits_Discounted'
    # for resiliency projects grouped by uncertainty scenario and asset
    BCAbyAsset = final_table.loc[:, ['ID-Uncertainty Scenario', 'Asset', 'Resiliency Project',
                                     'NetBenefits_Discounted']].groupby(['ID-Uncertainty Scenario', 'Asset',
                                                                         'Resiliency Project'],
                                                                        as_index=False, sort=False).mean()
    BCAbyAsset['RegretAsset'] = BCAbyAsset.groupby(['ID-Uncertainty Scenario', 'Asset'])['NetBenefits_Discounted'].rank(
        method='dense', ascending=False)
    final_table = pd.merge(final_table, BCAbyAsset.loc[:, ['ID-Uncertainty Scenario', 'Asset', 'Resiliency Project',
                                                           'RegretAsset']],
                           how='left', on=['ID-Uncertainty Scenario', 'Asset', 'Resiliency Project'])

    final_table = final_table.drop(labels=['ID-Resiliency-Scenario-Baseline', 'total_repair', 'Damage (%)',
                                           'ID-Resiliency-Scenario_base', 'initTripslevels_base', 'initVMTlevels_base',
                                           'initPHTlevels_base', 'expTripslevels_base', 'expVMTlevels_base',
                                           'expPHTlevels_base', 'Hazard Event'],
                                   axis=1)
    final_table = final_table.drop(labels=['initTripslevels_baseyr', 'initVMTlevels_baseyr', 'initPHTlevels_baseyr',
                                           'initTripslevels_baseyr_base', 'initVMTlevels_baseyr_base',
                                           'initPHTlevels_baseyr_base', 'initTripslevel_dollar_baseyr',
                                           'initVMTlevel_dollar_baseyr', 'initPHTlevel_dollar_baseyr', 'expTripslevels_baseyr',
                                           'expVMTlevels_baseyr', 'expPHTlevels_baseyr', 'expTripslevels_baseyr_base',
                                           'expVMTlevels_baseyr_base', 'expPHTlevels_baseyr_base',
                                           'expTripslevel_dollar_baseyr', 'expVMTlevel_dollar_baseyr',
                                           'expPHTlevel_dollar_baseyr', 'damTripslevels_baseyr', 'damVMTlevels_baseyr',
                                           'damPHTlevels_baseyr', 'damTripslevel_dollar_baseyr', 'damVMTlevel_dollar_baseyr',
                                           'damPHTlevel_dollar_baseyr', 'initTripsvsBase_baseyr', 'initVMTvsBase_baseyr',
                                           'initPHTvsBase_baseyr', 'initTripsvsBase_dollar_baseyr',
                                           'initVMTvsBase_dollar_baseyr', 'initPHTvsBase_dollar_baseyr',
                                           'expTripsvsBase_baseyr', 'expVMTvsBase_baseyr', 'expPHTvsBase_baseyr',
                                           'expTripsvsBase_dollar_baseyr', 'expVMTvsBase_dollar_baseyr',
                                           'expPHTvsBase_dollar_baseyr', 'damTripsvsBase_baseyr', 'damVMTvsBase_baseyr',
                                           'damPHTvsBase_baseyr', 'damTripsvsBase_dollar_baseyr', 'damVMTvsBase_dollar_baseyr',
                                           'damPHTvsBase_dollar_baseyr', 'initSafetyvsBase_baseyr', 'expSafetyvsBase_baseyr',
                                           'damSafetyvsBase_baseyr'],
                                   axis=1)

    # output in a form easily read by Tableau
    tableau_names = {'ID-Resiliency-Scenario': 'IDResiliencyScenario', 'ID-Uncertainty Scenario': 'IDScenario',
                     'Total Duration': 'DurationofEntireEventdays', 'Exposure Recovery Path': 'Exposurerecoverypath',
                     'Economic': 'EconomicScenario', 'Trip Loss Elasticity': 'TripElasticity',
                     'Future Event Frequency': 'FutureEventFrequency', 'Resiliency Project': 'ResiliencyProject',
                     'Project Name': 'ProjectName',
                     'repair_time': 'DamageDuration', 'AssetDamagelevel_dollar': 'RepairCleanupCosts',
                     'AssetDamagevsBase_dollar': 'RepairCleanupCostSavings', 'damage_repair': 'RepairCostSavings'}
    final_table.rename(tableau_names, axis='columns', inplace=True)

    # print out output file with all baseline scenarios for records
    all_baselines_file = os.path.join(output_folder, 'bca_metrics_' + str(cfg['run_id']) + '.csv')
    logger.debug("Size of BCA table with all baseline scenarios: {}".format(final_table.shape))
    with open(all_baselines_file, "w", newline='') as f:
        final_table.to_csv(f, index=False)
        logger.result("BCA table with all baseline scenarios written to {}".format(all_baselines_file))

    # if regret analysis, zero out BCA values
    if roi_analysis_type == 'Regret':
        final_table['NetBenefits_Discounted'] = 0

    # assign 'IDResiliencyScenario' = 0, 'Project Group' = 'None' for all baseline averages
    tableau_table = final_table.groupby(['IDScenario', 'ResiliencyProject', 'ProjectName', 'Asset',
                                         'ResiliencyProjectAsset', 'Year', 'EconomicScenario',
                                         'Exposurerecoverypath', 'DamageRecoveryPath'],
                                        as_index=False, sort=False).mean()
    tableau_table.loc[tableau_table['ResiliencyProject'] == 'no', ['IDResiliencyScenario']] = 0
    tableau_table.loc[tableau_table['ResiliencyProject'] == 'no', ['Project Group']] = 'None'

    tableau_file = os.path.join(output_folder, 'tableau_input_file_' + str(cfg['run_id']) + '.xlsx')
    logger.result("Tableau dashboard input table written to {}".format(tableau_file))
    tableau_table.to_excel(tableau_file, sheet_name="Sheet1", index=False,
                           columns=['Year', 'IDResiliencyScenario', 'IDScenario', 'IDScenarioNoHazard',
                                    'EconomicScenario', 'TripElasticity', 'FutureEventFrequency', 'HazardDim1',
                                    'HazardDim2', 'Event Probability', 'DurationofEntireEventdays',
                                    'Exposurerecoverypath', 'DamageRecoveryPath', 'Project Group', 'ResiliencyProject',
                                    'ProjectName',
                                    'Asset', 'ResiliencyProjectAsset', 'ProjectCosts_Discounted',
                                    'TotalNetBenefits_Discounted', 'NetBenefits_Discounted', 'Benefits_Discounted',
                                    'ExpBenefits_Discounted', 'RepairCleanupCostSavings_Discounted',
                                    'DamBenefits_Discounted', 'BCR_Discounted', 'RegretAll', 'RegretScenario',
                                    'RegretAsset', 'initTripslevels', 'initTripslevel_dollar', 'initTripsvsBase',
                                    'initTripsvsBase_dollar', 'initVMTlevels', 'initVMTlevel_dollar', 'initVMTvsBase',
                                    'initVMTvsBase_dollar', 'initPHTlevels', 'initPHTlevel_dollar', 'initPHTvsBase',
                                    'initPHTvsBase_dollar', 'expTripslevels', 'expTripslevel_dollar', 'expTripsvsBase',
                                    'expTripsvsBase_dollar', 'expVMTlevels', 'expVMTlevel_dollar', 'expVMTvsBase',
                                    'expVMTvsBase_dollar', 'expPHTlevels', 'expPHTlevel_dollar', 'expPHTvsBase',
                                    'expPHTvsBase_dollar', 'damTripslevels', 'damTripslevel_dollar', 'damTripsvsBase',
                                    'damTripsvsBase_dollar', 'damVMTlevels', 'damVMTlevel_dollar', 'damVMTvsBase',
                                    'damVMTvsBase_dollar', 'damPHTlevels', 'damPHTlevel_dollar', 'damPHTvsBase',
                                    'damPHTvsBase_dollar', 'AssetDamagelevels', 'RepairCleanupCosts',
                                    'AssetDamagevsBase', 'RepairCleanupCostSavings', 'DamageDuration',
                                    'RepairCostSavings', 'initSafety_Discounted', 'expSafety_Discounted',
                                    'damSafety_Discounted', 'initEmissions_Discounted', 'expEmissions_Discounted',
                                    'damEmissions_Discounted', 'TotalMaintenanceCosts_Discounted', 'TotalResidual_Discounted'])

    tableau_dir = prepare_tableau_assets(tableau_file, output_folder, cfg, logger)
    logger.result("Tableau dashboard written to directory {}".format(tableau_dir))

    logger.info("Finished: recovery analysis module")


# ==============================================================================


# check ROI inputs based on ROI Analysis Type parameter
def check_roi_required_inputs(input_folder, cfg, logger):
    logger.info("Start: check_roi_required_inputs")
    is_covered = 1

    model_params_file = os.path.join(input_folder, 'Model_Parameters.xlsx')
    if not os.path.exists(model_params_file):
        logger.error("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
        raise Exception("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
    model_params = pd.read_excel(model_params_file, sheet_name='Hazards',
                                 usecols=['Hazard Event', 'Event Probability in Start Year'],
                                 converters={'Hazard Event': str, 'Event Probability in Start Year': float})

    project_table = os.path.join(input_folder, 'LookupTables', 'project_info.csv')
    if not os.path.exists(project_table):
        logger.error("RESILIENCE PROJECTS FILE ERROR: {} could not be found".format(project_table))
        raise Exception("RESILIENCE PROJECTS FILE ERROR: {} could not be found".format(project_table))
    projects = pd.read_csv(project_table, usecols=['Project ID', 'Project Cost', 'Project Lifespan'],
                           converters={'Project ID': str, 'Project Cost': str, 'Project Lifespan': int})
    # convert 'Project Cost' column to float type
    projects['Estimated Project Cost'] = projects['Project Cost'].replace('[\$,]', '', regex=True).astype(float)

    # check 'Project Lifespan' for positive integers
    if (projects['Project Lifespan'] <= 0).any():
        logger.error("Note: Project lifespan must be a positive integer (e.g., number of years). If running a breakeven analysis, enter any positive integer--the value will be ignored.")

    if cfg['roi_analysis_type'] == 'BCA':
        # Need actual project costs, hazard probabilities
        logger.info("ROI analysis type is BCA: looking for actual project costs and hazard probabilities")
        if (projects['Estimated Project Cost'] == 0).all():
            logger.warning("Note: All project costs have been set to zero. BCA analysis requires actual project costs.")
        if (model_params['Event Probability in Start Year'] == 0).all() or (model_params['Event Probability in Start Year'] == 1).all():
            logger.warning("Note: All hazard probabilities have been set to zero or one. BCA analysis requires actual hazard probabilities.")
    elif cfg['roi_analysis_type'] == 'Regret':
        # Need actual project costs, hazard probabilities set to 1
        logger.info("ROI analysis type is Regret: looking for actual project costs and all hazard probabilities set to 1")
        if (projects['Estimated Project Cost'] == 0).all():
            logger.warning("Note: All project costs have been set to zero. Regret analysis requires actual project costs.")
        if (model_params['Event Probability in Start Year'] != 1).any():
            logger.error("Note: Not all hazard probabilities have been set to 1. Regret analysis requires all hazard probabilities set to 1.")
            is_covered = 0
    elif cfg['roi_analysis_type'] == 'Breakeven':
        # If project cost is nonzero, give an warning
        # Need actual hazard probabilities
        logger.info("ROI analysis type is Breakeven: looking for actual hazard probabilities and ignoring project costs")
        if (projects['Estimated Project Cost'] != 0).any():
            logger.warning("Note: Not all project costs have been set to zero. Breakeven analysis ignores any project cost inputs.")
        if (model_params['Event Probability in Start Year'] == 0).all() or (model_params['Event Probability in Start Year'] == 1).all():
            logger.warning("Note: All hazard probabilities have been set to zero or one. Breakeven analysis requires actual hazard probabilities.")

    logger.info("Finished: check_roi_required_inputs")
    return is_covered


# ==============================================================================


# create a Tableau dashboard from templates in the config folder and the results XLSX file
def prepare_tableau_assets(report_file, output_folder, cfg, logger):
    logger.info("Start: prepare_tableau_assets")
    tab_dir_name = 'tableau_report_' + str(cfg['run_id']) + '_' + datetime.datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
    tableau_directory = os.path.join(output_folder, 'Reports', tab_dir_name)
    if not os.path.exists(tableau_directory):
        os.makedirs(tableau_directory)

    # copy the relative path tableau TWB file from the config directory to the tableau report directory
    logger.debug("copying the twb file from config folder to the tableau report folder")
    config_directory = os.path.join(os.path.abspath(os.path.join(os.getcwd(), os.pardir)), 'config')
    root_twb_location = os.path.join(config_directory, 'template_dashboard.twb')
    if not os.path.exists(root_twb_location):
        logger.error("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_twb_location))
        raise Exception("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_twb_location))
    root_graphic1_location = os.path.join(config_directory, 'tableau_images', 'dictionary_noBackground.png')
    if not os.path.exists(root_graphic1_location):
        logger.error("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_graphic1_location))
        raise Exception("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_graphic1_location))
    root_graphic2_location = os.path.join(config_directory, 'tableau_images', 'images.png')
    if not os.path.exists(root_graphic2_location):
        logger.error("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_graphic2_location))
        raise Exception("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_graphic2_location))
    root_graphic3_location = os.path.join(config_directory, 'tableau_images', 'Picture4.png')
    if not os.path.exists(root_graphic3_location):
        logger.error("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_graphic3_location))
        raise Exception("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_graphic3_location))
    shutil.copy(root_twb_location, os.path.join(tableau_directory, 'tableau_dashboard.twb'))
    shutil.copy(root_graphic1_location, tableau_directory)
    shutil.copy(root_graphic2_location, tableau_directory)
    shutil.copy(root_graphic3_location, tableau_directory)

    # copy tableau report to the tableau report directory
    logger.debug("copying the tableau report xlsx file to the tableau report directory")
    shutil.copy(report_file, os.path.join(tableau_directory, 'tableau_input_file.xlsx'))

    # create packaged workbook for tableau reader compatibility
    twbx_dashboard_filename = os.path.join(tableau_directory, 'tableau_dashboard.twbx')
    zipObj = zipfile.ZipFile(twbx_dashboard_filename, 'w', zipfile.ZIP_DEFLATED)

    # add multiple files to the zip
    zipObj.write(os.path.join(tableau_directory, 'tableau_dashboard.twb'), 'tableau_dashboard.twb')
    zipObj.write(os.path.join(tableau_directory, 'tableau_input_file.xlsx'), 'tableau_input_file.xlsx')
    zipObj.write(os.path.join(tableau_directory, 'dictionary_noBackground.png'), 'dictionary_noBackground.png')
    zipObj.write(os.path.join(tableau_directory, 'images.png'), 'images.png')
    zipObj.write(os.path.join(tableau_directory, 'Picture4.png'), 'Picture4.png')

    # close the Zip File
    zipObj.close()

    # delete the original files for clean up
    os.remove(os.path.join(tableau_directory, 'tableau_dashboard.twb'))
    os.remove(os.path.join(tableau_directory, 'tableau_input_file.xlsx'))
    os.remove(os.path.join(tableau_directory, 'dictionary_noBackground.png'))
    os.remove(os.path.join(tableau_directory, 'images.png'))
    os.remove(os.path.join(tableau_directory, 'Picture4.png'))

    # open tableau dashboard for Windows
    os.startfile(twbx_dashboard_filename)

    logger.info("Finished: prepare_tableau_assets")

    return tableau_directory
