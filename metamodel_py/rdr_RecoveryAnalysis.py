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

    logger.debug("Reading in parameters for ROI analysis")
    roi_analysis_type = cfg['roi_analysis_type']

    start_year = cfg['start_year']
    end_year = cfg['end_year']
    base_year = cfg['base_year']
    future_year = cfg['future_year']

    # cost inputs and outputs are reported in dollar_year units
    dollar_year = cfg['dollar_year']
    discount_factor = cfg['discount_factor']
    co2_discount_factor = cfg['co2_discount_factor']

    # vehicle occupancy rates
    vehicle_occupancy = cfg['vehicle_occupancy']
    if cfg['calc_transit_metrics']:
        vehicle_occupancy_b = cfg['vehicle_occupancy_bus']
        vehicle_occupancy_lr = cfg['vehicle_occupancy_light_rail']
        vehicle_occupancy_hr = cfg['vehicle_occupancy_heavy_rail']

    # vehicle operating costs
    miles_cost = cfg['veh_oper_cost']
    if cfg['calc_transit_metrics']:
        miles_cost_b = cfg['veh_oper_cost_bus']
        miles_cost_lr = cfg['veh_oper_cost_light_rail']
        miles_cost_hr = cfg['veh_oper_cost_heavy_rail']

    # value of time and transit fare parameters
    hours_cost = cfg['vot_per_hour']
    if cfg['calc_transit_metrics']:
        hours_wait_cost = cfg['vot_wait_per_hour']
        transit_fare = cfg['transit_fare']

    # maintenance and redeployment parameters
    maintenance = cfg['maintenance']
    redeployment = cfg['redeployment']

    # safety, noise, and emissions parameters
    safety_cost = cfg['safety_cost']
    noise_cost = cfg['noise_cost']
    non_co2_cost = cfg['non_co2_cost']
    co2_cost = cfg['co2_cost']
    if cfg['calc_transit_metrics']:
        safety_cost_b = cfg['safety_cost_bus']
        noise_cost_b = cfg['noise_cost_bus']
        non_co2_cost_b = cfg['non_co2_cost_bus']
        co2_cost_b = cfg['co2_cost_bus']

    logger.config("ReportingParameters: ROI analysis type is {}".format(roi_analysis_type))
    logger.config("ReportingParameters: period of analysis is {} to {}".format(str(start_year), str(end_year)))
    logger.config(("ReportingParameters: base year runs are for year {}, ".format(str(base_year)) +
                   "future year runs are for year {}".format(str(future_year))))
    logger.config("ReportingParameters: monetary values are in units of year {} dollars".format(str(dollar_year)))
    logger.config(("ReportingParameters: general discounting factor = {}, ".format(str(discount_factor)) +
                   "CO2 discounting factor = {}".format(str(co2_discount_factor))))
    logger.config("ReportingParameters: average vehicle occupancy = {}".format(str(vehicle_occupancy)))
    if cfg['calc_transit_metrics']:
        logger.config("ReportingParameters: transit vehicle occupancies for bus = {}, light rail = {}, heavy rail = {}".format(str(vehicle_occupancy_b),
                                                                                                                               str(vehicle_occupancy_lr),
                                                                                                                               str(vehicle_occupancy_hr)))
    logger.config("ReportingParameters: cost of vehicle-mile = ${}, cost of person-hour = ${}".format(str(miles_cost),
                                                                                                      str(hours_cost)))
    if cfg['calc_transit_metrics']:
        logger.config("ReportingParameters: transit operating costs for bus = ${}, light rail = ${}, heavy rail = ${}".format(str(miles_cost_b),
                                                                                                                              str(miles_cost_lr),
                                                                                                                              str(miles_cost_hr)))
        logger.config("ReportingParameters: value of transit wait time = ${}".format(str(hours_wait_cost)))
        logger.config("ReportingParameters: transit fare = ${}".format(str(transit_fare)))
    logger.config("ReportingParameters: maintenance cost toggle set to {}, redeployment cost toggle set to {}".format(str(maintenance),
                                                                                                                      str(redeployment)))
    logger.config("ReportingParameters: safety cost = {}, noise cost = {}".format(str(safety_cost), str(noise_cost)))
    logger.config("ReportingParameters: co2 cost = {}, non co2 cost = {}".format(str(co2_cost), str(non_co2_cost)))

    if cfg['calc_transit_metrics']:
        logger.config("ReportingParameters: bus safety cost = {}, bus noise cost = {}".format(str(safety_cost_b), str(noise_cost_b)))
        logger.config("ReportingParameters: bus co2 cost = {}, bus non co2 cost = {}".format(str(co2_cost_b), str(non_co2_cost_b)))

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

    # reads in car and transit mode columns if cfg['calc_transit_metrics'] is True
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
    if cfg['cfg_type'] == 'config':
        model_params_file = os.path.join(input_folder, 'Model_Parameters.xlsx')
        if not os.path.exists(model_params_file):
            logger.error("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
            raise Exception("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
        hazard_levels = make_hazard_levels(model_params_file, 'config', logger)
    else:  # cfg_type = 'json'
        hazard_levels = make_hazard_levels(cfg, 'json', logger)

    hazard_levels = hazard_levels.loc[:, ['Hazard Level', 'HazardDim1', 'HazardDim2', 'Hazard Event',
                                          'Recovery', 'Event Probability in Start Year']]
    logger.debug("Size of hazard information table: {}".format(hazard_levels.shape))

    project_table = os.path.join(input_folder, 'LookupTables', 'project_info.csv')
    if not os.path.exists(project_table):
        logger.error("RESILIENCE PROJECTS FILE ERROR: {} could not be found".format(project_table))
        raise Exception("RESILIENCE PROJECTS FILE ERROR: {} could not be found".format(project_table))
    
    usecols = ['Project ID', 'Project Name', 'Asset', 'Project Cost', 'Project Lifespan']
    converters = {'Project ID': str, 'Project Name': str, 'Asset': str, 'Project Cost': str,
                  'Project Lifespan': int}
    if maintenance:
        usecols.append('Annual Maintenance Cost')
        converters['Annual Maintenance Cost'] = str
    if redeployment:
        usecols.append('Redeployment Cost')
        converters['Redeployment Cost'] = str

    projects = pd.read_csv(project_table, usecols=usecols, converters=converters)
    # convert 'Project Cost', 'Annual Maintenance Cost', 'Redeployment Cost' columns to float type
    projects['Estimated Project Cost'] = projects['Project Cost'].replace('[\$,]', '', regex=True).astype(float)
    projects['Estimated Maintenance Cost'] = 0
    projects['Estimated Redeployment Cost'] = 0

    # assign maintenance and redeployment costs only if they are set to be included in config
    if maintenance:
        projects['Estimated Maintenance Cost'] = projects['Annual Maintenance Cost'].replace('[\$,]', '', regex=True).astype(float)
    if redeployment:
        projects['Estimated Redeployment Cost'] = projects['Redeployment Cost'].replace('[\$,]', '', regex=True).astype(float)
    
    logger.debug("Size of resilience project information table: {}".format(projects.shape))

    # create table of unique project-asset rows
    project_list = projects.drop_duplicates(ignore_index=True)
    # row in project table is created for baseline 'no' case with Estimated Project Cost = 0
    temp_row = {'Project ID': 'no', 'Project Name': 'No Vulnerability Projects', 'Asset': 'No Asset',
                'Estimated Project Cost': 0.0, 'Project Lifespan': end_year - start_year + 1,
                'Estimated Maintenance Cost': 0.0,
                'Estimated Redeployment Cost': 0.0}
    project_list = pd.concat([project_list, pd.DataFrame(temp_row, index=[0])], ignore_index=True)

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
    if cfg['calc_transit_metrics']:
        merged2 = pd.merge(merged2, base_regression_output.loc[:, ['hazard', 'recovery', 'trips', 'miles', 'hours',
                                                                   'lr_trips', 'hr_trips', 'bus_trips', 'car_trips',
                                                                   'lr_miles', 'hr_miles', 'bus_miles', 'car_miles',
                                                                   'lr_hours_wait', 'hr_hours_wait', 'bus_hours_wait',
                                                                   'lr_hours_enroute', 'hr_hours_enroute',
                                                                   'bus_hours_enroute', 'car_hours']],
                           how='left', left_on=['Hazard Event', 'Recovery'], right_on=['hazard', 'recovery'],
                           suffixes=(None, "_baseyr"), indicator=True)
    else:
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
    if cfg['calc_transit_metrics']:
        merged2['initTripslevels_lr'] = np.where(merged2['Stage Number'] == 1, merged2['lr_trips'], 0.0)
        merged2['initTripslevels_hr'] = np.where(merged2['Stage Number'] == 1, merged2['hr_trips'], 0.0)
        merged2['initTripslevels_b'] = np.where(merged2['Stage Number'] == 1, merged2['bus_trips'], 0.0)
        merged2['initTripslevels_c'] = np.where(merged2['Stage Number'] == 1, merged2['car_trips'], 0.0)
        merged2['initVMTlevels_lr'] = np.where(merged2['Stage Number'] == 1, merged2['lr_miles'] / vehicle_occupancy_lr, 0.0)
        merged2['initVMTlevels_hr'] = np.where(merged2['Stage Number'] == 1, merged2['hr_miles'] / vehicle_occupancy_hr, 0.0)
        merged2['initVMTlevels_b'] = np.where(merged2['Stage Number'] == 1, merged2['bus_miles'] / vehicle_occupancy_b, 0.0)
        merged2['initVMTlevels_c'] = np.where(merged2['Stage Number'] == 1, merged2['car_miles'] / vehicle_occupancy, 0.0)
        merged2['initPHTlevels_lr_w'] = np.where(merged2['Stage Number'] == 1, merged2['lr_hours_wait'], 0.0)
        merged2['initPHTlevels_hr_w'] = np.where(merged2['Stage Number'] == 1, merged2['hr_hours_wait'], 0.0)
        merged2['initPHTlevels_b_w'] = np.where(merged2['Stage Number'] == 1, merged2['bus_hours_wait'], 0.0)
        merged2['initPHTlevels_lr_e'] = np.where(merged2['Stage Number'] == 1, merged2['lr_hours_enroute'], 0.0)
        merged2['initPHTlevels_hr_e'] = np.where(merged2['Stage Number'] == 1, merged2['hr_hours_enroute'], 0.0)
        merged2['initPHTlevels_b_e'] = np.where(merged2['Stage Number'] == 1, merged2['bus_hours_enroute'], 0.0)
        merged2['initPHTlevels_c'] = np.where(merged2['Stage Number'] == 1, merged2['car_hours'], 0.0)

        merged2['initTripslevels_lr_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['lr_trips_baseyr'], 0.0)
        merged2['initTripslevels_hr_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['hr_trips_baseyr'], 0.0)
        merged2['initTripslevels_b_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['bus_trips_baseyr'], 0.0)
        merged2['initTripslevels_c_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['car_trips_baseyr'], 0.0)
        merged2['initVMTlevels_lr_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['lr_miles_baseyr'] / vehicle_occupancy_lr, 0.0)
        merged2['initVMTlevels_hr_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['hr_miles_baseyr'] / vehicle_occupancy_hr, 0.0)
        merged2['initVMTlevels_b_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['bus_miles_baseyr'] / vehicle_occupancy_b, 0.0)
        merged2['initVMTlevels_c_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['car_miles_baseyr'] / vehicle_occupancy, 0.0)
        merged2['initPHTlevels_lr_w_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['lr_hours_wait_baseyr'], 0.0)
        merged2['initPHTlevels_hr_w_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['hr_hours_wait_baseyr'], 0.0)
        merged2['initPHTlevels_b_w_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['bus_hours_wait_baseyr'], 0.0)
        merged2['initPHTlevels_lr_e_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['lr_hours_enroute_baseyr'], 0.0)
        merged2['initPHTlevels_hr_e_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['hr_hours_enroute_baseyr'], 0.0)
        merged2['initPHTlevels_b_e_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['bus_hours_enroute_baseyr'], 0.0)
        merged2['initPHTlevels_c_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['car_hours_baseyr'], 0.0)

        merged2 = merged2.assign(initTripslevels=(merged2['initTripslevels_lr'] + merged2['initTripslevels_hr'] +
                                                  merged2['initTripslevels_b'] + merged2['initTripslevels_c']),
                                 initVMTlevels=(merged2['initVMTlevels_lr'] + merged2['initVMTlevels_hr'] +
                                                merged2['initVMTlevels_b'] + merged2['initVMTlevels_c']),
                                 initPHTlevels=(merged2['initPHTlevels_lr_w'] + merged2['initPHTlevels_hr_w'] +
                                                merged2['initPHTlevels_b_w'] + merged2['initPHTlevels_lr_e'] +
                                                merged2['initPHTlevels_hr_e'] + merged2['initPHTlevels_b_e'] +
                                                merged2['initPHTlevels_c']),
                                 initTripslevels_baseyr=(merged2['initTripslevels_lr_baseyr'] + merged2['initTripslevels_hr_baseyr'] +
                                                         merged2['initTripslevels_b_baseyr'] + merged2['initTripslevels_c_baseyr']),
                                 initVMTlevels_baseyr=(merged2['initVMTlevels_lr_baseyr'] + merged2['initVMTlevels_hr_baseyr'] +
                                                       merged2['initVMTlevels_b_baseyr'] + merged2['initVMTlevels_c_baseyr']),
                                 initPHTlevels_baseyr=(merged2['initPHTlevels_lr_w_baseyr'] + merged2['initPHTlevels_hr_w_baseyr'] +
                                                       merged2['initPHTlevels_b_w_baseyr'] + merged2['initPHTlevels_lr_e_baseyr'] +
                                                       merged2['initPHTlevels_hr_e_baseyr'] + merged2['initPHTlevels_b_e_baseyr'] +
                                                       merged2['initPHTlevels_c_baseyr']))
    else:
        merged2['initTripslevels'] = np.where(merged2['Stage Number'] == 1, merged2['trips'], 0.0)
        merged2['initVMTlevels'] = np.where(merged2['Stage Number'] == 1, merged2['miles'] / vehicle_occupancy, 0.0)
        merged2['initPHTlevels'] = np.where(merged2['Stage Number'] == 1, merged2['hours'], 0.0)
        merged2['initTripslevels_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['trips_baseyr'], 0.0)
        merged2['initVMTlevels_baseyr'] = np.where(merged2['Stage Number'] == 1,
                                                   merged2['miles_baseyr'] / vehicle_occupancy, 0.0)
        merged2['initPHTlevels_baseyr'] = np.where(merged2['Stage Number'] == 1, merged2['hours_baseyr'], 0.0)

    # calculate new columns 'expTripslevels'/'expVMTlevels'/'expPHTlevels' by multiplying
    # 'Stage Duration' and 'trips'/'miles'/'hours' (and dividing by vehicle_occupancy for VMT)
    if cfg['calc_transit_metrics']:
        merged2 = merged2.assign(expTripslevels_lr=merged2['Stage Duration'] * merged2['lr_trips'],
                                 expTripslevels_hr=merged2['Stage Duration'] * merged2['hr_trips'],
                                 expTripslevels_b=merged2['Stage Duration'] * merged2['bus_trips'],
                                 expTripslevels_c=merged2['Stage Duration'] * merged2['car_trips'],
                                 expVMTlevels_lr=merged2['Stage Duration'] * merged2['lr_miles']/vehicle_occupancy_lr,
                                 expVMTlevels_hr=merged2['Stage Duration'] * merged2['hr_miles']/vehicle_occupancy_hr,
                                 expVMTlevels_b=merged2['Stage Duration'] * merged2['bus_miles']/vehicle_occupancy_b,
                                 expVMTlevels_c=merged2['Stage Duration'] * merged2['car_miles']/vehicle_occupancy,
                                 expPHTlevels_lr_w=merged2['Stage Duration'] * merged2['lr_hours_wait'],
                                 expPHTlevels_hr_w=merged2['Stage Duration'] * merged2['hr_hours_wait'],
                                 expPHTlevels_b_w=merged2['Stage Duration'] * merged2['bus_hours_wait'],
                                 expPHTlevels_lr_e=merged2['Stage Duration'] * merged2['lr_hours_enroute'],
                                 expPHTlevels_hr_e=merged2['Stage Duration'] * merged2['hr_hours_enroute'],
                                 expPHTlevels_b_e=merged2['Stage Duration'] * merged2['bus_hours_enroute'],
                                 expPHTlevels_c=merged2['Stage Duration'] * merged2['car_hours'])
        merged2 = merged2.assign(expTripslevels_lr_baseyr=merged2['Stage Duration'] * merged2['lr_trips_baseyr'],
                                 expTripslevels_hr_baseyr=merged2['Stage Duration'] * merged2['hr_trips_baseyr'],
                                 expTripslevels_b_baseyr=merged2['Stage Duration'] * merged2['bus_trips_baseyr'],
                                 expTripslevels_c_baseyr=merged2['Stage Duration'] * merged2['car_trips_baseyr'],
                                 expVMTlevels_lr_baseyr=merged2['Stage Duration'] * merged2['lr_miles_baseyr']/vehicle_occupancy_lr,
                                 expVMTlevels_hr_baseyr=merged2['Stage Duration'] * merged2['hr_miles_baseyr']/vehicle_occupancy_hr,
                                 expVMTlevels_b_baseyr=merged2['Stage Duration'] * merged2['bus_miles_baseyr']/vehicle_occupancy_b,
                                 expVMTlevels_c_baseyr=merged2['Stage Duration'] * merged2['car_miles_baseyr']/vehicle_occupancy,
                                 expPHTlevels_lr_w_baseyr=merged2['Stage Duration'] * merged2['lr_hours_wait_baseyr'],
                                 expPHTlevels_hr_w_baseyr=merged2['Stage Duration'] * merged2['hr_hours_wait_baseyr'],
                                 expPHTlevels_b_w_baseyr=merged2['Stage Duration'] * merged2['bus_hours_wait_baseyr'],
                                 expPHTlevels_lr_e_baseyr=merged2['Stage Duration'] * merged2['lr_hours_enroute_baseyr'],
                                 expPHTlevels_hr_e_baseyr=merged2['Stage Duration'] * merged2['hr_hours_enroute_baseyr'],
                                 expPHTlevels_b_e_baseyr=merged2['Stage Duration'] * merged2['bus_hours_enroute_baseyr'],
                                 expPHTlevels_c_baseyr=merged2['Stage Duration'] * merged2['car_hours_baseyr'])

        merged2 = merged2.assign(expTripslevels=(merged2['expTripslevels_lr'] + merged2['expTripslevels_hr'] +
                                                 merged2['expTripslevels_b'] + merged2['expTripslevels_c']),
                                 expVMTlevels=(merged2['expVMTlevels_lr'] + merged2['expVMTlevels_hr'] +
                                               merged2['expVMTlevels_b'] + merged2['expVMTlevels_c']),
                                 expPHTlevels=(merged2['expPHTlevels_lr_w'] + merged2['expPHTlevels_hr_w'] +
                                               merged2['expPHTlevels_b_w'] + merged2['expPHTlevels_lr_e'] +
                                               merged2['expPHTlevels_hr_e'] + merged2['expPHTlevels_b_e'] +
                                               merged2['expPHTlevels_c']),
                                 expTripslevels_baseyr=(merged2['expTripslevels_lr_baseyr'] + merged2['expTripslevels_hr_baseyr'] +
                                                        merged2['expTripslevels_b_baseyr'] + merged2['expTripslevels_c_baseyr']),
                                 expVMTlevels_baseyr=(merged2['expVMTlevels_lr_baseyr'] + merged2['expVMTlevels_hr_baseyr'] +
                                                      merged2['expVMTlevels_b_baseyr'] + merged2['expVMTlevels_c_baseyr']),
                                 expPHTlevels_baseyr=(merged2['expPHTlevels_lr_w_baseyr'] + merged2['expPHTlevels_hr_w_baseyr'] +
                                                      merged2['expPHTlevels_b_w_baseyr'] + merged2['expPHTlevels_lr_e_baseyr'] +
                                                      merged2['expPHTlevels_hr_e_baseyr'] + merged2['expPHTlevels_b_e_baseyr'] +
                                                      merged2['expPHTlevels_c_baseyr']))
    else:
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
    if cfg['calc_transit_metrics']:
        maximum_recovery_data = merged2.loc[merged2.reset_index().groupby(['ID-Resiliency-Scenario'])['recovery_depth'].idxmax(),
                                            ['ID-Resiliency-Scenario', 'lr_trips', 'hr_trips', 'bus_trips', 'car_trips',
                                             'lr_miles', 'hr_miles', 'bus_miles', 'car_miles', 'lr_hours_wait',
                                             'hr_hours_wait', 'bus_hours_wait', 'lr_hours_enroute', 'hr_hours_enroute',
                                             'bus_hours_enroute', 'car_hours', 'lr_trips_baseyr', 'hr_trips_baseyr',
                                             'bus_trips_baseyr', 'car_trips_baseyr', 'lr_miles_baseyr', 'hr_miles_baseyr',
                                             'bus_miles_baseyr', 'car_miles_baseyr', 'lr_hours_wait_baseyr',
                                             'hr_hours_wait_baseyr', 'bus_hours_wait_baseyr', 'lr_hours_enroute_baseyr',
                                             'hr_hours_enroute_baseyr', 'bus_hours_enroute_baseyr', 'car_hours_baseyr']]
        maximum_recovery_data['lr_miles'] = maximum_recovery_data['lr_miles'] / vehicle_occupancy_lr
        maximum_recovery_data['hr_miles'] = maximum_recovery_data['hr_miles'] / vehicle_occupancy_hr
        maximum_recovery_data['bus_miles'] = maximum_recovery_data['bus_miles'] / vehicle_occupancy_b
        maximum_recovery_data['car_miles'] = maximum_recovery_data['car_miles'] / vehicle_occupancy
        maximum_recovery_data['lr_miles_baseyr'] = maximum_recovery_data['lr_miles_baseyr'] / vehicle_occupancy_lr
        maximum_recovery_data['hr_miles_baseyr'] = maximum_recovery_data['hr_miles_baseyr'] / vehicle_occupancy_hr
        maximum_recovery_data['bus_miles_baseyr'] = maximum_recovery_data['bus_miles_baseyr'] / vehicle_occupancy_b
        maximum_recovery_data['car_miles_baseyr'] = maximum_recovery_data['car_miles_baseyr'] / vehicle_occupancy
        maximum_recovery_data = maximum_recovery_data.assign(initTripslevels=(maximum_recovery_data['lr_trips'] +
                                                                              maximum_recovery_data['hr_trips'] +
                                                                              maximum_recovery_data['bus_trips'] +
                                                                              maximum_recovery_data['car_trips']),
                                                             initVMTlevels=(maximum_recovery_data['lr_miles'] +
                                                                            maximum_recovery_data['hr_miles'] +
                                                                            maximum_recovery_data['bus_miles'] +
                                                                            maximum_recovery_data['car_miles']),
                                                             initPHTlevels=(maximum_recovery_data['lr_hours_wait'] +
                                                                            maximum_recovery_data['hr_hours_wait'] +
                                                                            maximum_recovery_data['bus_hours_wait'] +
                                                                            maximum_recovery_data['lr_hours_enroute'] +
                                                                            maximum_recovery_data['hr_hours_enroute'] +
                                                                            maximum_recovery_data['bus_hours_enroute'] +
                                                                            maximum_recovery_data['car_hours']),
                                                             initTripslevels_baseyr=(maximum_recovery_data['lr_trips_baseyr'] +
                                                                                     maximum_recovery_data['hr_trips_baseyr'] +
                                                                                     maximum_recovery_data['bus_trips_baseyr'] +
                                                                                     maximum_recovery_data['car_trips_baseyr']),
                                                             initVMTlevels_baseyr=(maximum_recovery_data['lr_miles_baseyr'] +
                                                                                   maximum_recovery_data['hr_miles_baseyr'] +
                                                                                   maximum_recovery_data['bus_miles_baseyr'] +
                                                                                   maximum_recovery_data['car_miles_baseyr']),
                                                             initPHTlevels_baseyr=(maximum_recovery_data['lr_hours_wait_baseyr'] +
                                                                                   maximum_recovery_data['hr_hours_wait_baseyr'] +
                                                                                   maximum_recovery_data['bus_hours_wait_baseyr'] +
                                                                                   maximum_recovery_data['lr_hours_enroute_baseyr'] +
                                                                                   maximum_recovery_data['hr_hours_enroute_baseyr'] +
                                                                                   maximum_recovery_data['bus_hours_enroute_baseyr'] +
                                                                                   maximum_recovery_data['car_hours_baseyr']))
        maximum_recovery_data.rename({'lr_trips': 'initTripslevels_lr', 'hr_trips': 'initTripslevels_hr',
                                      'bus_trips': 'initTripslevels_b', 'car_trips': 'initTripslevels_c',
                                      'lr_miles': 'initVMTlevels_lr', 'hr_miles': 'initVMTlevels_hr',
                                      'bus_miles': 'initVMTlevels_b', 'car_miles': 'initVMTlevels_c',
                                      'lr_hours_wait': 'initPHTlevels_lr_w', 'hr_hours_wait': 'initPHTlevels_hr_w',
                                      'bus_hours_wait': 'initPHTlevels_b_w', 'lr_hours_enroute': 'initPHTlevels_lr_e',
                                      'hr_hours_enroute': 'initPHTlevels_hr_e', 'bus_hours_enroute': 'initPHTlevels_b_e',
                                      'car_hours': 'initPHTlevels_c',
                                      'lr_trips_baseyr': 'initTripslevels_lr_baseyr', 'hr_trips_baseyr': 'initTripslevels_hr_baseyr',
                                      'bus_trips_baseyr': 'initTripslevels_b_baseyr', 'car_trips_baseyr': 'initTripslevels_c_baseyr',
                                      'lr_miles_baseyr': 'initVMTlevels_lr_baseyr', 'hr_miles_baseyr': 'initVMTlevels_hr_baseyr',
                                      'bus_miles_baseyr': 'initVMTlevels_b_baseyr', 'car_miles_baseyr': 'initVMTlevels_c_baseyr',
                                      'lr_hours_wait_baseyr': 'initPHTlevels_lr_w_baseyr', 'hr_hours_wait_baseyr': 'initPHTlevels_hr_w_baseyr',
                                      'bus_hours_wait_baseyr': 'initPHTlevels_b_w_baseyr', 'lr_hours_enroute_baseyr': 'initPHTlevels_lr_e_baseyr',
                                      'hr_hours_enroute_baseyr': 'initPHTlevels_hr_e_baseyr', 'bus_hours_enroute_baseyr': 'initPHTlevels_b_e_baseyr',
                                      'car_hours_baseyr': 'initPHTlevels_c_baseyr'},
                                     axis='columns', inplace=True)
    else:
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
    if cfg['calc_transit_metrics']:
        hazard_recession_data = merged2.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
                                                'initPHTlevels', 'initTripslevels_baseyr', 'initVMTlevels_baseyr',
                                                'initPHTlevels_baseyr', 'expTripslevels', 'expVMTlevels', 'expPHTlevels',
                                                'expTripslevels_baseyr', 'expVMTlevels_baseyr',
                                                'expPHTlevels_baseyr', 'initTripslevels_lr', 'initTripslevels_hr',
                                                'initTripslevels_b', 'initTripslevels_c', 'initVMTlevels_lr',
                                                'initVMTlevels_hr', 'initVMTlevels_b', 'initVMTlevels_c', 'initPHTlevels_lr_w',
                                                'initPHTlevels_hr_w', 'initPHTlevels_b_w', 'initPHTlevels_lr_e',
                                                'initPHTlevels_hr_e', 'initPHTlevels_b_e', 'initPHTlevels_c',
                                                'initTripslevels_lr_baseyr', 'initTripslevels_hr_baseyr',
                                                'initTripslevels_b_baseyr', 'initTripslevels_c_baseyr',
                                                'initVMTlevels_lr_baseyr', 'initVMTlevels_hr_baseyr',
                                                'initVMTlevels_b_baseyr', 'initVMTlevels_c_baseyr',
                                                'initPHTlevels_lr_w_baseyr', 'initPHTlevels_hr_w_baseyr',
                                                'initPHTlevels_b_w_baseyr', 'initPHTlevels_lr_e_baseyr',
                                                'initPHTlevels_hr_e_baseyr', 'initPHTlevels_b_e_baseyr',
                                                'initPHTlevels_c_baseyr', 'expTripslevels_lr', 'expTripslevels_hr',
                                                'expTripslevels_b', 'expTripslevels_c', 'expVMTlevels_lr',
                                                'expVMTlevels_hr', 'expVMTlevels_b', 'expVMTlevels_c', 'expPHTlevels_lr_w',
                                                'expPHTlevels_hr_w', 'expPHTlevels_b_w', 'expPHTlevels_lr_e',
                                                'expPHTlevels_hr_e', 'expPHTlevels_b_e', 'expPHTlevels_c',
                                                'expTripslevels_lr_baseyr', 'expTripslevels_hr_baseyr',
                                                'expTripslevels_b_baseyr', 'expTripslevels_c_baseyr',
                                                'expVMTlevels_lr_baseyr', 'expVMTlevels_hr_baseyr',
                                                'expVMTlevels_b_baseyr', 'expVMTlevels_c_baseyr',
                                                'expPHTlevels_lr_w_baseyr', 'expPHTlevels_hr_w_baseyr',
                                                'expPHTlevels_b_w_baseyr', 'expPHTlevels_lr_e_baseyr',
                                                'expPHTlevels_hr_e_baseyr', 'expPHTlevels_b_e_baseyr',
                                                'expPHTlevels_c_baseyr']].groupby('ID-Resiliency-Scenario', as_index=False,
                                                                                  sort=False).sum()
    else:
        hazard_recession_data = merged2.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
                                                'initPHTlevels', 'initTripslevels_baseyr', 'initVMTlevels_baseyr',
                                                'initPHTlevels_baseyr', 'expTripslevels', 'expVMTlevels', 'expPHTlevels',
                                                'expTripslevels_baseyr', 'expVMTlevels_baseyr',
                                                'expPHTlevels_baseyr']].groupby('ID-Resiliency-Scenario', as_index=False,
                                                                                sort=False).sum()

    # calculate dollar values for Trips/VMT/PHT
    logger.debug("calculating dollar values for Trips/VMT/PHT metrics")
    if cfg['calc_transit_metrics']:
        hazard_recession_data = hazard_recession_data.assign(initTripslevel_dollar=((0.5 * vehicle_occupancy_lr *
                                                                                     (hazard_recession_data['initTripslevels_lr'] *
                                                                                      hazard_recession_data['initVMTlevels_lr'] /
                                                                                      (hazard_recession_data['initPHTlevels_lr_w'] +
                                                                                       hazard_recession_data['initPHTlevels_lr_e'])).fillna(0)) +
                                                                                    (0.5 * vehicle_occupancy_hr *
                                                                                     (hazard_recession_data['initTripslevels_hr'] *
                                                                                      hazard_recession_data['initVMTlevels_hr'] /
                                                                                      (hazard_recession_data['initPHTlevels_hr_w'] +
                                                                                       hazard_recession_data['initPHTlevels_hr_e'])).fillna(0)) +
                                                                                    (0.5 * vehicle_occupancy_b *
                                                                                     (hazard_recession_data['initTripslevels_b'] *
                                                                                      hazard_recession_data['initVMTlevels_b'] /
                                                                                      (hazard_recession_data['initPHTlevels_b_w'] +
                                                                                       hazard_recession_data['initPHTlevels_b_e'])).fillna(0)) +
                                                                                    (0.5 * vehicle_occupancy *
                                                                                     (hazard_recession_data['initTripslevels_c'] *
                                                                                      hazard_recession_data['initVMTlevels_c'] /
                                                                                      hazard_recession_data['initPHTlevels_c']).fillna(0)) +
                                                                                    transit_fare * (hazard_recession_data['initTripslevels_lr'] +
                                                                                                    hazard_recession_data['initTripslevels_hr'] +
                                                                                                    hazard_recession_data['initTripslevels_b'])),
                                                             initVMTlevel_dollar=(hazard_recession_data['initVMTlevels_lr'] * miles_cost_lr +
                                                                                  hazard_recession_data['initVMTlevels_hr'] * miles_cost_hr +
                                                                                  hazard_recession_data['initVMTlevels_b'] * miles_cost_b +
                                                                                  hazard_recession_data['initVMTlevels_c'] * miles_cost),
                                                             initPHTlevel_dollar=(hours_cost * (hazard_recession_data['initPHTlevels_lr_e'] +
                                                                                                hazard_recession_data['initPHTlevels_hr_e'] +
                                                                                                hazard_recession_data['initPHTlevels_b_e'] +
                                                                                                hazard_recession_data['initPHTlevels_c']) +
                                                                                  hours_wait_cost * (hazard_recession_data['initPHTlevels_lr_w'] +
                                                                                                     hazard_recession_data['initPHTlevels_hr_w'] +
                                                                                                     hazard_recession_data['initPHTlevels_b_w'])),
                                                             expTripslevel_dollar=((0.5 * vehicle_occupancy_lr *
                                                                                    (hazard_recession_data['expTripslevels_lr'] *
                                                                                     hazard_recession_data['expVMTlevels_lr'] /
                                                                                     (hazard_recession_data['expPHTlevels_lr_w'] +
                                                                                      hazard_recession_data['expPHTlevels_lr_e'])).fillna(0)) +
                                                                                   (0.5 * vehicle_occupancy_hr *
                                                                                    (hazard_recession_data['expTripslevels_hr'] *
                                                                                     hazard_recession_data['expVMTlevels_hr'] /
                                                                                     (hazard_recession_data['expPHTlevels_hr_w'] +
                                                                                      hazard_recession_data['expPHTlevels_hr_e'])).fillna(0)) +
                                                                                   (0.5 * vehicle_occupancy_b *
                                                                                    (hazard_recession_data['expTripslevels_b'] *
                                                                                     hazard_recession_data['expVMTlevels_b'] /
                                                                                     (hazard_recession_data['expPHTlevels_b_w'] +
                                                                                      hazard_recession_data['expPHTlevels_b_e'])).fillna(0)) +
                                                                                   (0.5 * vehicle_occupancy *
                                                                                    (hazard_recession_data['expTripslevels_c'] *
                                                                                     hazard_recession_data['expVMTlevels_c'] /
                                                                                     hazard_recession_data['expPHTlevels_c']).fillna(0)) +
                                                                                   transit_fare * (hazard_recession_data['expTripslevels_lr'] +
                                                                                                   hazard_recession_data['expTripslevels_hr'] +
                                                                                                   hazard_recession_data['expTripslevels_b'])),
                                                             expVMTlevel_dollar=(hazard_recession_data['expVMTlevels_lr'] * miles_cost_lr +
                                                                                 hazard_recession_data['expVMTlevels_hr'] * miles_cost_hr +
                                                                                 hazard_recession_data['expVMTlevels_b'] * miles_cost_b +
                                                                                 hazard_recession_data['expVMTlevels_c'] * miles_cost),
                                                             expPHTlevel_dollar=(hours_cost * (hazard_recession_data['expPHTlevels_lr_e'] +
                                                                                               hazard_recession_data['expPHTlevels_hr_e'] +
                                                                                               hazard_recession_data['expPHTlevels_b_e'] +
                                                                                               hazard_recession_data['expPHTlevels_c']) +
                                                                                 hours_wait_cost * (hazard_recession_data['expPHTlevels_lr_w'] +
                                                                                                    hazard_recession_data['expPHTlevels_hr_w'] +
                                                                                                    hazard_recession_data['expPHTlevels_b_w'])))
        hazard_recession_data = hazard_recession_data.assign(initTripslevel_dollar_baseyr=((0.5 * vehicle_occupancy_lr *
                                                                                            (hazard_recession_data['initTripslevels_lr_baseyr'] *
                                                                                             hazard_recession_data['initVMTlevels_lr_baseyr'] /
                                                                                             (hazard_recession_data['initPHTlevels_lr_w_baseyr'] +
                                                                                              hazard_recession_data['initPHTlevels_lr_e_baseyr'])).fillna(0)) +
                                                                                           (0.5 * vehicle_occupancy_hr *
                                                                                            (hazard_recession_data['initTripslevels_hr_baseyr'] *
                                                                                             hazard_recession_data['initVMTlevels_hr_baseyr'] /
                                                                                             (hazard_recession_data['initPHTlevels_hr_w_baseyr'] +
                                                                                              hazard_recession_data['initPHTlevels_hr_e_baseyr'])).fillna(0)) +
                                                                                           (0.5 * vehicle_occupancy_b *
                                                                                            (hazard_recession_data['initTripslevels_b_baseyr'] *
                                                                                             hazard_recession_data['initVMTlevels_b_baseyr'] /
                                                                                             (hazard_recession_data['initPHTlevels_b_w_baseyr'] +
                                                                                              hazard_recession_data['initPHTlevels_b_e_baseyr'])).fillna(0)) +
                                                                                           (0.5 * vehicle_occupancy *
                                                                                            (hazard_recession_data['initTripslevels_c_baseyr'] *
                                                                                             hazard_recession_data['initVMTlevels_c_baseyr'] /
                                                                                             hazard_recession_data['initPHTlevels_c_baseyr']).fillna(0)) +
                                                                                           transit_fare * (hazard_recession_data['initTripslevels_lr_baseyr'] +
                                                                                                           hazard_recession_data['initTripslevels_hr_baseyr'] +
                                                                                                           hazard_recession_data['initTripslevels_b_baseyr'])),
                                                             initVMTlevel_dollar_baseyr=(hazard_recession_data['initVMTlevels_lr_baseyr'] * miles_cost_lr +
                                                                                         hazard_recession_data['initVMTlevels_hr_baseyr'] * miles_cost_hr +
                                                                                         hazard_recession_data['initVMTlevels_b_baseyr'] * miles_cost_b +
                                                                                         hazard_recession_data['initVMTlevels_c_baseyr'] * miles_cost),
                                                             initPHTlevel_dollar_baseyr=(hours_cost * (hazard_recession_data['initPHTlevels_lr_e_baseyr'] +
                                                                                                       hazard_recession_data['initPHTlevels_hr_e_baseyr'] +
                                                                                                       hazard_recession_data['initPHTlevels_b_e_baseyr'] +
                                                                                                       hazard_recession_data['initPHTlevels_c_baseyr']) +
                                                                                         hours_wait_cost * (hazard_recession_data['initPHTlevels_lr_w_baseyr'] +
                                                                                                            hazard_recession_data['initPHTlevels_hr_w_baseyr'] +
                                                                                                            hazard_recession_data['initPHTlevels_b_w_baseyr'])),
                                                             expTripslevel_dollar_baseyr=((0.5 * vehicle_occupancy_lr *
                                                                                           (hazard_recession_data['expTripslevels_lr_baseyr'] *
                                                                                            hazard_recession_data['expVMTlevels_lr_baseyr'] /
                                                                                            (hazard_recession_data['expPHTlevels_lr_w_baseyr'] +
                                                                                             hazard_recession_data['expPHTlevels_lr_e_baseyr'])).fillna(0)) +
                                                                                          (0.5 * vehicle_occupancy_hr *
                                                                                           (hazard_recession_data['expTripslevels_hr_baseyr'] *
                                                                                            hazard_recession_data['expVMTlevels_hr_baseyr'] /
                                                                                            (hazard_recession_data['expPHTlevels_hr_w_baseyr'] +
                                                                                             hazard_recession_data['expPHTlevels_hr_e_baseyr'])).fillna(0)) +
                                                                                          (0.5 * vehicle_occupancy_b *
                                                                                           (hazard_recession_data['expTripslevels_b_baseyr'] *
                                                                                            hazard_recession_data['expVMTlevels_b_baseyr'] /
                                                                                            (hazard_recession_data['expPHTlevels_b_w_baseyr'] +
                                                                                             hazard_recession_data['expPHTlevels_b_e_baseyr'])).fillna(0)) +
                                                                                          (0.5 * vehicle_occupancy *
                                                                                           (hazard_recession_data['expTripslevels_c_baseyr'] *
                                                                                            hazard_recession_data['expVMTlevels_c_baseyr'] /
                                                                                            hazard_recession_data['expPHTlevels_c_baseyr']).fillna(0)) +
                                                                                          transit_fare * (hazard_recession_data['expTripslevels_lr_baseyr'] +
                                                                                                          hazard_recession_data['expTripslevels_hr_baseyr'] +
                                                                                                          hazard_recession_data['expTripslevels_b_baseyr'])),
                                                             expVMTlevel_dollar_baseyr=(hazard_recession_data['expVMTlevels_lr_baseyr'] * miles_cost_lr +
                                                                                        hazard_recession_data['expVMTlevels_hr_baseyr'] * miles_cost_hr +
                                                                                        hazard_recession_data['expVMTlevels_b_baseyr'] * miles_cost_b +
                                                                                        hazard_recession_data['expVMTlevels_c_baseyr'] * miles_cost),
                                                             expPHTlevel_dollar_baseyr=(hours_cost * (hazard_recession_data['expPHTlevels_lr_e_baseyr'] +
                                                                                                      hazard_recession_data['expPHTlevels_hr_e_baseyr'] +
                                                                                                      hazard_recession_data['expPHTlevels_b_e_baseyr'] +
                                                                                                      hazard_recession_data['expPHTlevels_c_baseyr']) +
                                                                                        hours_wait_cost * (hazard_recession_data['expPHTlevels_lr_w_baseyr'] +
                                                                                                           hazard_recession_data['expPHTlevels_hr_w_baseyr'] +
                                                                                                           hazard_recession_data['expPHTlevels_b_w_baseyr'])))
    else:
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
    # pull in columns for 'Asset', 'Estimated Project Cost', 'Project Lifespan', 'Estimated Maintenance Cost', and 'Estimated Redeployment Cost' from project_list
    merged4 = pd.merge(merged3, project_list.loc[:, ['Project ID', 'Project Name', 'Asset', 'Estimated Project Cost',
                                                     'Project Lifespan', 'Estimated Maintenance Cost',
                                                     'Estimated Redeployment Cost']],
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

    # placeholder
    merged7 = merged6.copy()

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
    if cfg['calc_transit_metrics']:
        merged7['damTripslevels_lr'] = 0.5 * (merged7['initTripslevels_lr'] + merged7['initTripslevels_lr_max']) * merged7['repair_time']
        merged7['damTripslevels_hr'] = 0.5 * (merged7['initTripslevels_hr'] + merged7['initTripslevels_hr_max']) * merged7['repair_time']
        merged7['damTripslevels_b'] = 0.5 * (merged7['initTripslevels_b'] + merged7['initTripslevels_b_max']) * merged7['repair_time']
        merged7['damTripslevels_c'] = 0.5 * (merged7['initTripslevels_c'] + merged7['initTripslevels_c_max']) * merged7['repair_time']
        merged7['damVMTlevels_lr'] = 0.5 * (merged7['initVMTlevels_lr'] + merged7['initVMTlevels_lr_max']) * merged7['repair_time']
        merged7['damVMTlevels_hr'] = 0.5 * (merged7['initVMTlevels_hr'] + merged7['initVMTlevels_hr_max']) * merged7['repair_time']
        merged7['damVMTlevels_b'] = 0.5 * (merged7['initVMTlevels_b'] + merged7['initVMTlevels_b_max']) * merged7['repair_time']
        merged7['damVMTlevels_c'] = 0.5 * (merged7['initVMTlevels_c'] + merged7['initVMTlevels_c_max']) * merged7['repair_time']
        merged7['damPHTlevels_lr_w'] = 0.5 * (merged7['initPHTlevels_lr_w'] + merged7['initPHTlevels_lr_w_max']) * merged7['repair_time']
        merged7['damPHTlevels_hr_w'] = 0.5 * (merged7['initPHTlevels_hr_w'] + merged7['initPHTlevels_hr_w_max']) * merged7['repair_time']
        merged7['damPHTlevels_b_w'] = 0.5 * (merged7['initPHTlevels_b_w'] + merged7['initPHTlevels_b_w_max']) * merged7['repair_time']
        merged7['damPHTlevels_lr_e'] = 0.5 * (merged7['initPHTlevels_lr_e'] + merged7['initPHTlevels_lr_e_max']) * merged7['repair_time']
        merged7['damPHTlevels_hr_e'] = 0.5 * (merged7['initPHTlevels_hr_e'] + merged7['initPHTlevels_hr_e_max']) * merged7['repair_time']
        merged7['damPHTlevels_b_e'] = 0.5 * (merged7['initPHTlevels_b_e'] + merged7['initPHTlevels_b_e_max']) * merged7['repair_time']
        merged7['damPHTlevels_c'] = 0.5 * (merged7['initPHTlevels_c'] + merged7['initPHTlevels_c_max']) * merged7['repair_time']
        merged7['damTripslevels_lr_baseyr'] = 0.5 * (merged7['initTripslevels_lr_baseyr'] +
                                                     merged7['initTripslevels_lr_baseyr_max']) * merged7['repair_time']
        merged7['damTripslevels_hr_baseyr'] = 0.5 * (merged7['initTripslevels_hr_baseyr'] +
                                                     merged7['initTripslevels_hr_baseyr_max']) * merged7['repair_time']
        merged7['damTripslevels_b_baseyr'] = 0.5 * (merged7['initTripslevels_b_baseyr'] +
                                                    merged7['initTripslevels_b_baseyr_max']) * merged7['repair_time']
        merged7['damTripslevels_c_baseyr'] = 0.5 * (merged7['initTripslevels_c_baseyr'] +
                                                    merged7['initTripslevels_c_baseyr_max']) * merged7['repair_time']
        merged7['damVMTlevels_lr_baseyr'] = 0.5 * (merged7['initVMTlevels_lr_baseyr'] +
                                                   merged7['initVMTlevels_lr_baseyr_max']) * merged7['repair_time']
        merged7['damVMTlevels_hr_baseyr'] = 0.5 * (merged7['initVMTlevels_hr_baseyr'] +
                                                   merged7['initVMTlevels_hr_baseyr_max']) * merged7['repair_time']
        merged7['damVMTlevels_b_baseyr'] = 0.5 * (merged7['initVMTlevels_b_baseyr'] +
                                                  merged7['initVMTlevels_b_baseyr_max']) * merged7['repair_time']
        merged7['damVMTlevels_c_baseyr'] = 0.5 * (merged7['initVMTlevels_c_baseyr'] +
                                                  merged7['initVMTlevels_c_baseyr_max']) * merged7['repair_time']
        merged7['damPHTlevels_lr_w_baseyr'] = 0.5 * (merged7['initPHTlevels_lr_w_baseyr'] +
                                                     merged7['initPHTlevels_lr_w_baseyr_max']) * merged7['repair_time']
        merged7['damPHTlevels_hr_w_baseyr'] = 0.5 * (merged7['initPHTlevels_hr_w_baseyr'] +
                                                     merged7['initPHTlevels_hr_w_baseyr_max']) * merged7['repair_time']
        merged7['damPHTlevels_b_w_baseyr'] = 0.5 * (merged7['initPHTlevels_b_w_baseyr'] +
                                                    merged7['initPHTlevels_b_w_baseyr_max']) * merged7['repair_time']
        merged7['damPHTlevels_lr_e_baseyr'] = 0.5 * (merged7['initPHTlevels_lr_e_baseyr'] +
                                                     merged7['initPHTlevels_lr_e_baseyr_max']) * merged7['repair_time']
        merged7['damPHTlevels_hr_e_baseyr'] = 0.5 * (merged7['initPHTlevels_hr_e_baseyr'] +
                                                     merged7['initPHTlevels_hr_e_baseyr_max']) * merged7['repair_time']
        merged7['damPHTlevels_b_e_baseyr'] = 0.5 * (merged7['initPHTlevels_b_e_baseyr'] +
                                                    merged7['initPHTlevels_b_e_baseyr_max']) * merged7['repair_time']
        merged7['damPHTlevels_c_baseyr'] = 0.5 * (merged7['initPHTlevels_c_baseyr'] +
                                                  merged7['initPHTlevels_c_baseyr_max']) * merged7['repair_time']
        merged7 = merged7.assign(damTripslevels=(merged7['damTripslevels_lr'] + merged7['damTripslevels_hr'] +
                                                 merged7['damTripslevels_b'] + merged7['damTripslevels_c']),
                                 damVMTlevels=(merged7['damVMTlevels_lr'] + merged7['damVMTlevels_hr'] +
                                               merged7['damVMTlevels_b'] + merged7['damVMTlevels_c']),
                                 damPHTlevels=(merged7['damPHTlevels_lr_w'] + merged7['damPHTlevels_hr_w'] +
                                               merged7['damPHTlevels_b_w'] + merged7['damPHTlevels_lr_e'] +
                                               merged7['damPHTlevels_hr_e'] + merged7['damPHTlevels_b_e'] +
                                               merged7['damPHTlevels_c']),
                                 damTripslevels_baseyr=(merged7['damTripslevels_lr_baseyr'] + merged7['damTripslevels_hr_baseyr'] +
                                                        merged7['damTripslevels_b_baseyr'] + merged7['damTripslevels_c_baseyr']),
                                 damVMTlevels_baseyr=(merged7['damVMTlevels_lr_baseyr'] + merged7['damVMTlevels_hr_baseyr'] +
                                                      merged7['damVMTlevels_b_baseyr'] + merged7['damVMTlevels_c_baseyr']),
                                 damPHTlevels_baseyr=(merged7['damPHTlevels_lr_w_baseyr'] + merged7['damPHTlevels_hr_w_baseyr'] +
                                                      merged7['damPHTlevels_b_w_baseyr'] + merged7['damPHTlevels_lr_e_baseyr'] +
                                                      merged7['damPHTlevels_hr_e_baseyr'] + merged7['damPHTlevels_b_e_baseyr'] +
                                                      merged7['damPHTlevels_c_baseyr']))
        merged7 = merged7.assign(damTripslevel_dollar=((0.5 * vehicle_occupancy_lr *
                                                        (merged7['damTripslevels_lr'] *
                                                         merged7['damVMTlevels_lr'] /
                                                         (merged7['damPHTlevels_lr_w'] +
                                                          merged7['damPHTlevels_lr_e'])).fillna(0)) +
                                                       (0.5 * vehicle_occupancy_hr *
                                                        (merged7['damTripslevels_hr'] *
                                                         merged7['damVMTlevels_hr'] /
                                                         (merged7['damPHTlevels_hr_w'] +
                                                          merged7['damPHTlevels_hr_e'])).fillna(0)) +
                                                       (0.5 * vehicle_occupancy_b *
                                                        (merged7['damTripslevels_b'] *
                                                         merged7['damVMTlevels_b'] /
                                                         (merged7['damPHTlevels_b_w'] +
                                                          merged7['damPHTlevels_b_e'])).fillna(0)) +
                                                       (0.5 * vehicle_occupancy *
                                                        (merged7['damTripslevels_c'] *
                                                         merged7['damVMTlevels_c'] /
                                                         merged7['damPHTlevels_c']).fillna(0)) +
                                                       transit_fare * (merged7['damTripslevels_lr'] +
                                                                       merged7['damTripslevels_hr'] +
                                                                       merged7['damTripslevels_b'])),
                                 damVMTlevel_dollar=(merged7['damVMTlevels_lr'] * miles_cost_lr +
                                                     merged7['damVMTlevels_hr'] * miles_cost_hr +
                                                     merged7['damVMTlevels_b'] * miles_cost_b +
                                                     merged7['damVMTlevels_c'] * miles_cost),
                                 damPHTlevel_dollar=(hours_cost * (merged7['damPHTlevels_lr_e'] +
                                                                   merged7['damPHTlevels_hr_e'] +
                                                                   merged7['damPHTlevels_b_e'] +
                                                                   merged7['damPHTlevels_c']) +
                                                     hours_wait_cost * (merged7['damPHTlevels_lr_w'] +
                                                                        merged7['damPHTlevels_hr_w'] +
                                                                        merged7['damPHTlevels_b_w'])),
                                 damTripslevel_dollar_baseyr=((0.5 * vehicle_occupancy_lr *
                                                               (merged7['damTripslevels_lr_baseyr'] *
                                                                merged7['damVMTlevels_lr_baseyr'] /
                                                                (merged7['damPHTlevels_lr_w_baseyr'] +
                                                                 merged7['damPHTlevels_lr_e_baseyr'])).fillna(0)) +
                                                              (0.5 * vehicle_occupancy_hr *
                                                               (merged7['damTripslevels_hr_baseyr'] *
                                                                merged7['damVMTlevels_hr_baseyr'] /
                                                                (merged7['damPHTlevels_hr_w_baseyr'] +
                                                                 merged7['damPHTlevels_hr_e_baseyr'])).fillna(0)) +
                                                              (0.5 * vehicle_occupancy_b *
                                                               (merged7['damTripslevels_b_baseyr'] *
                                                                merged7['damVMTlevels_b_baseyr'] /
                                                                (merged7['damPHTlevels_b_w_baseyr'] +
                                                                 merged7['damPHTlevels_b_e_baseyr'])).fillna(0)) +
                                                              (0.5 * vehicle_occupancy *
                                                               (merged7['damTripslevels_c_baseyr'] *
                                                                merged7['damVMTlevels_c_baseyr'] /
                                                                merged7['damPHTlevels_c_baseyr']).fillna(0)) +
                                                              transit_fare * (merged7['damTripslevels_lr_baseyr'] +
                                                                              merged7['damTripslevels_hr_baseyr'] +
                                                                              merged7['damTripslevels_b_baseyr'])),
                                 damVMTlevel_dollar_baseyr=(merged7['damVMTlevels_lr_baseyr'] * miles_cost_lr +
                                                            merged7['damVMTlevels_hr_baseyr'] * miles_cost_hr +
                                                            merged7['damVMTlevels_b_baseyr'] * miles_cost_b +
                                                            merged7['damVMTlevels_c_baseyr'] * miles_cost),
                                 damPHTlevel_dollar_baseyr=(hours_cost * (merged7['damPHTlevels_lr_e_baseyr'] +
                                                                          merged7['damPHTlevels_hr_e_baseyr'] +
                                                                          merged7['damPHTlevels_b_e_baseyr'] +
                                                                          merged7['damPHTlevels_c_baseyr']) +
                                                            hours_wait_cost * (merged7['damPHTlevels_lr_w_baseyr'] +
                                                                               merged7['damPHTlevels_hr_w_baseyr'] +
                                                                               merged7['damPHTlevels_b_w_baseyr'])))
    else:
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

    # use 'ID-Resiliency-Scenario-Baseline' to join to other baseline scenario metrics
    if cfg['calc_transit_metrics']:
        merged7 = pd.merge(merged7, merged7.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
                                                    'initPHTlevels', 'initTripslevels_baseyr', 'initVMTlevels_baseyr',
                                                    'initPHTlevels_baseyr', 'expTripslevels', 'expVMTlevels',
                                                    'expPHTlevels', 'expTripslevels_baseyr', 'expVMTlevels_baseyr',
                                                    'expPHTlevels_baseyr', 'initTripslevel_dollar', 'initVMTlevel_dollar',
                                                    'initPHTlevel_dollar', 'initTripslevel_dollar_baseyr', 'initVMTlevel_dollar_baseyr',
                                                    'initPHTlevel_dollar_baseyr', 'expTripslevel_dollar', 'expVMTlevel_dollar',
                                                    'expPHTlevel_dollar', 'expTripslevel_dollar_baseyr', 'expVMTlevel_dollar_baseyr',
                                                    'expPHTlevel_dollar_baseyr', 'damTripslevel_dollar', 'damVMTlevel_dollar',
                                                    'damPHTlevel_dollar', 'damTripslevel_dollar_baseyr', 'damVMTlevel_dollar_baseyr',
                                                    'damPHTlevel_dollar_baseyr', 'initTripslevels_lr', 'initTripslevels_hr',
                                                    'initTripslevels_b', 'initTripslevels_c', 'initVMTlevels_lr',
                                                    'initVMTlevels_hr', 'initVMTlevels_b', 'initVMTlevels_c', 'initPHTlevels_lr_w',
                                                    'initPHTlevels_hr_w', 'initPHTlevels_b_w', 'initPHTlevels_lr_e',
                                                    'initPHTlevels_hr_e', 'initPHTlevels_b_e', 'initPHTlevels_c',
                                                    'initTripslevels_lr_baseyr', 'initTripslevels_hr_baseyr',
                                                    'initTripslevels_b_baseyr', 'initTripslevels_c_baseyr',
                                                    'initVMTlevels_lr_baseyr', 'initVMTlevels_hr_baseyr',
                                                    'initVMTlevels_b_baseyr', 'initVMTlevels_c_baseyr',
                                                    'initPHTlevels_lr_w_baseyr', 'initPHTlevels_hr_w_baseyr',
                                                    'initPHTlevels_b_w_baseyr', 'initPHTlevels_lr_e_baseyr',
                                                    'initPHTlevels_hr_e_baseyr', 'initPHTlevels_b_e_baseyr',
                                                    'initPHTlevels_c_baseyr', 'expTripslevels_lr', 'expTripslevels_hr',
                                                    'expTripslevels_b', 'expTripslevels_c', 'expVMTlevels_lr',
                                                    'expVMTlevels_hr', 'expVMTlevels_b', 'expVMTlevels_c', 'expPHTlevels_lr_w',
                                                    'expPHTlevels_hr_w', 'expPHTlevels_b_w', 'expPHTlevels_lr_e',
                                                    'expPHTlevels_hr_e', 'expPHTlevels_b_e', 'expPHTlevels_c',
                                                    'expTripslevels_lr_baseyr', 'expTripslevels_hr_baseyr',
                                                    'expTripslevels_b_baseyr', 'expTripslevels_c_baseyr',
                                                    'expVMTlevels_lr_baseyr', 'expVMTlevels_hr_baseyr',
                                                    'expVMTlevels_b_baseyr', 'expVMTlevels_c_baseyr',
                                                    'expPHTlevels_lr_w_baseyr', 'expPHTlevels_hr_w_baseyr',
                                                    'expPHTlevels_b_w_baseyr', 'expPHTlevels_lr_e_baseyr',
                                                    'expPHTlevels_hr_e_baseyr', 'expPHTlevels_b_e_baseyr',
                                                    'expPHTlevels_c_baseyr']],
                           how='left', left_on='ID-Resiliency-Scenario-Baseline', right_on='ID-Resiliency-Scenario',
                           suffixes=[None, '_base'], indicator=True)
    else:
        merged7 = pd.merge(merged7, merged7.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
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

    # calculate metrics for damage repair period for baseline
    # NOTE: fields are missing values for baseline scenarios
    if cfg['calc_transit_metrics']:
        merged7['damTripslevels_lr_base'] = 0.5 * (merged7['initTripslevels_lr_base'] + merged7['initTripslevels_lr_max']) * merged7['repair_time_base']
        merged7['damTripslevels_hr_base'] = 0.5 * (merged7['initTripslevels_hr_base'] + merged7['initTripslevels_hr_max']) * merged7['repair_time_base']
        merged7['damTripslevels_b_base'] = 0.5 * (merged7['initTripslevels_b_base'] + merged7['initTripslevels_b_max']) * merged7['repair_time_base']
        merged7['damTripslevels_c_base'] = 0.5 * (merged7['initTripslevels_c_base'] + merged7['initTripslevels_c_max']) * merged7['repair_time_base']
        merged7['damVMTlevels_lr_base'] = 0.5 * (merged7['initVMTlevels_lr_base'] + merged7['initVMTlevels_lr_max']) * merged7['repair_time_base']
        merged7['damVMTlevels_hr_base'] = 0.5 * (merged7['initVMTlevels_hr_base'] + merged7['initVMTlevels_hr_max']) * merged7['repair_time_base']
        merged7['damVMTlevels_b_base'] = 0.5 * (merged7['initVMTlevels_b_base'] + merged7['initVMTlevels_b_max']) * merged7['repair_time_base']
        merged7['damVMTlevels_c_base'] = 0.5 * (merged7['initVMTlevels_c_base'] + merged7['initVMTlevels_c_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_lr_w_base'] = 0.5 * (merged7['initPHTlevels_lr_w_base'] + merged7['initPHTlevels_lr_w_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_hr_w_base'] = 0.5 * (merged7['initPHTlevels_hr_w_base'] + merged7['initPHTlevels_hr_w_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_b_w_base'] = 0.5 * (merged7['initPHTlevels_b_w_base'] + merged7['initPHTlevels_b_w_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_lr_e_base'] = 0.5 * (merged7['initPHTlevels_lr_e_base'] + merged7['initPHTlevels_lr_e_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_hr_e_base'] = 0.5 * (merged7['initPHTlevels_hr_e_base'] + merged7['initPHTlevels_hr_e_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_b_e_base'] = 0.5 * (merged7['initPHTlevels_b_e_base'] + merged7['initPHTlevels_b_e_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_c_base'] = 0.5 * (merged7['initPHTlevels_c_base'] + merged7['initPHTlevels_c_max']) * merged7['repair_time_base']
        merged7['damTripslevels_lr_baseyr_base'] = 0.5 * (merged7['initTripslevels_lr_baseyr_base'] +
                                                     merged7['initTripslevels_lr_baseyr_max']) * merged7['repair_time_base']
        merged7['damTripslevels_hr_baseyr_base'] = 0.5 * (merged7['initTripslevels_hr_baseyr_base'] +
                                                     merged7['initTripslevels_hr_baseyr_max']) * merged7['repair_time_base']
        merged7['damTripslevels_b_baseyr_base'] = 0.5 * (merged7['initTripslevels_b_baseyr_base'] +
                                                    merged7['initTripslevels_b_baseyr_max']) * merged7['repair_time_base']
        merged7['damTripslevels_c_baseyr_base'] = 0.5 * (merged7['initTripslevels_c_baseyr_base'] +
                                                    merged7['initTripslevels_c_baseyr_max']) * merged7['repair_time_base']
        merged7['damVMTlevels_lr_baseyr_base'] = 0.5 * (merged7['initVMTlevels_lr_baseyr_base'] +
                                                   merged7['initVMTlevels_lr_baseyr_max']) * merged7['repair_time_base']
        merged7['damVMTlevels_hr_baseyr_base'] = 0.5 * (merged7['initVMTlevels_hr_baseyr_base'] +
                                                   merged7['initVMTlevels_hr_baseyr_max']) * merged7['repair_time_base']
        merged7['damVMTlevels_b_baseyr_base'] = 0.5 * (merged7['initVMTlevels_b_baseyr_base'] +
                                                  merged7['initVMTlevels_b_baseyr_max']) * merged7['repair_time_base']
        merged7['damVMTlevels_c_baseyr_base'] = 0.5 * (merged7['initVMTlevels_c_baseyr_base'] +
                                                  merged7['initVMTlevels_c_baseyr_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_lr_w_baseyr_base'] = 0.5 * (merged7['initPHTlevels_lr_w_baseyr_base'] +
                                                     merged7['initPHTlevels_lr_w_baseyr_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_hr_w_baseyr_base'] = 0.5 * (merged7['initPHTlevels_hr_w_baseyr_base'] +
                                                     merged7['initPHTlevels_hr_w_baseyr_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_b_w_baseyr_base'] = 0.5 * (merged7['initPHTlevels_b_w_baseyr_base'] +
                                                    merged7['initPHTlevels_b_w_baseyr_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_lr_e_baseyr_base'] = 0.5 * (merged7['initPHTlevels_lr_e_baseyr_base'] +
                                                     merged7['initPHTlevels_lr_e_baseyr_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_hr_e_baseyr_base'] = 0.5 * (merged7['initPHTlevels_hr_e_baseyr_base'] +
                                                     merged7['initPHTlevels_hr_e_baseyr_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_b_e_baseyr_base'] = 0.5 * (merged7['initPHTlevels_b_e_baseyr_base'] +
                                                    merged7['initPHTlevels_b_e_baseyr_max']) * merged7['repair_time_base']
        merged7['damPHTlevels_c_baseyr_base'] = 0.5 * (merged7['initPHTlevels_c_baseyr_base'] +
                                                  merged7['initPHTlevels_c_baseyr_max']) * merged7['repair_time_base']
        merged7 = merged7.assign(damTripslevels_base=(merged7['damTripslevels_lr_base'] + merged7['damTripslevels_hr_base'] +
                                                      merged7['damTripslevels_b_base'] + merged7['damTripslevels_c_base']),
                                 damVMTlevels_base=(merged7['damVMTlevels_lr_base'] + merged7['damVMTlevels_hr_base'] +
                                                    merged7['damVMTlevels_b_base'] + merged7['damVMTlevels_c_base']),
                                 damPHTlevels_base=(merged7['damPHTlevels_lr_w_base'] + merged7['damPHTlevels_hr_w_base'] +
                                                    merged7['damPHTlevels_b_w_base'] + merged7['damPHTlevels_lr_e_base'] +
                                                    merged7['damPHTlevels_hr_e_base'] + merged7['damPHTlevels_b_e_base'] +
                                                    merged7['damPHTlevels_c_base']),
                                 damTripslevels_baseyr_base=(merged7['damTripslevels_lr_baseyr_base'] + merged7['damTripslevels_hr_baseyr_base'] +
                                                             merged7['damTripslevels_b_baseyr_base'] + merged7['damTripslevels_c_baseyr_base']),
                                 damVMTlevels_baseyr_base=(merged7['damVMTlevels_lr_baseyr_base'] + merged7['damVMTlevels_hr_baseyr_base'] +
                                                           merged7['damVMTlevels_b_baseyr_base'] + merged7['damVMTlevels_c_baseyr_base']),
                                 damPHTlevels_baseyr_base=(merged7['damPHTlevels_lr_w_baseyr_base'] + merged7['damPHTlevels_hr_w_baseyr_base'] +
                                                           merged7['damPHTlevels_b_w_baseyr_base'] + merged7['damPHTlevels_lr_e_baseyr_base'] +
                                                           merged7['damPHTlevels_hr_e_baseyr_base'] + merged7['damPHTlevels_b_e_baseyr_base'] +
                                                           merged7['damPHTlevels_c_baseyr_base']))
        merged7 = merged7.assign(damTripslevel_dollar_base=((0.5 * vehicle_occupancy_lr *
                                                             (merged7['damTripslevels_lr_base'] *
                                                              merged7['damVMTlevels_lr_base'] /
                                                              (merged7['damPHTlevels_lr_w_base'] +
                                                               merged7['damPHTlevels_lr_e_base'])).fillna(0)) +
                                                            (0.5 * vehicle_occupancy_hr *
                                                             (merged7['damTripslevels_hr_base'] *
                                                              merged7['damVMTlevels_hr_base'] /
                                                              (merged7['damPHTlevels_hr_w_base'] +
                                                               merged7['damPHTlevels_hr_e_base'])).fillna(0)) +
                                                            (0.5 * vehicle_occupancy_b *
                                                             (merged7['damTripslevels_b_base'] *
                                                              merged7['damVMTlevels_b_base'] /
                                                              (merged7['damPHTlevels_b_w_base'] +
                                                               merged7['damPHTlevels_b_e_base'])).fillna(0)) +
                                                            (0.5 * vehicle_occupancy *
                                                             (merged7['damTripslevels_c_base'] *
                                                              merged7['damVMTlevels_c_base'] /
                                                              merged7['damPHTlevels_c_base']).fillna(0)) +
                                                            transit_fare * (merged7['damTripslevels_lr_base'] +
                                                                            merged7['damTripslevels_hr_base'] +
                                                                            merged7['damTripslevels_b_base'])),
                                 damVMTlevel_dollar_base=(merged7['damVMTlevels_lr_base'] * miles_cost_lr +
                                                          merged7['damVMTlevels_hr_base'] * miles_cost_hr +
                                                          merged7['damVMTlevels_b_base'] * miles_cost_b +
                                                          merged7['damVMTlevels_c_base'] * miles_cost),
                                 damPHTlevel_dollar_base=(hours_cost * (merged7['damPHTlevels_lr_e_base'] +
                                                                        merged7['damPHTlevels_hr_e_base'] +
                                                                        merged7['damPHTlevels_b_e_base'] +
                                                                        merged7['damPHTlevels_c_base']) +
                                                          hours_wait_cost * (merged7['damPHTlevels_lr_w_base'] +
                                                                             merged7['damPHTlevels_hr_w_base'] +
                                                                             merged7['damPHTlevels_b_w_base'])),
                                 damTripslevel_dollar_baseyr_base=((0.5 * vehicle_occupancy_lr *
                                                                    (merged7['damTripslevels_lr_baseyr_base'] *
                                                                     merged7['damVMTlevels_lr_baseyr_base'] /
                                                                     (merged7['damPHTlevels_lr_w_baseyr_base'] +
                                                                      merged7['damPHTlevels_lr_e_baseyr_base'])).fillna(0)) +
                                                                   (0.5 * vehicle_occupancy_hr *
                                                                    (merged7['damTripslevels_hr_baseyr_base'] *
                                                                     merged7['damVMTlevels_hr_baseyr_base'] /
                                                                     (merged7['damPHTlevels_hr_w_baseyr_base'] +
                                                                      merged7['damPHTlevels_hr_e_baseyr_base'])).fillna(0)) +
                                                                   (0.5 * vehicle_occupancy_b *
                                                                    (merged7['damTripslevels_b_baseyr_base'] *
                                                                     merged7['damVMTlevels_b_baseyr_base'] /
                                                                     (merged7['damPHTlevels_b_w_baseyr_base'] +
                                                                      merged7['damPHTlevels_b_e_baseyr_base'])).fillna(0)) +
                                                                   (0.5 * vehicle_occupancy *
                                                                    (merged7['damTripslevels_c_baseyr_base'] *
                                                                     merged7['damVMTlevels_c_baseyr_base'] /
                                                                     merged7['damPHTlevels_c_baseyr_base']).fillna(0)) +
                                                                   transit_fare * (merged7['damTripslevels_lr_baseyr_base'] +
                                                                                   merged7['damTripslevels_hr_baseyr_base'] +
                                                                                   merged7['damTripslevels_b_baseyr_base'])),
                                 damVMTlevel_dollar_baseyr_base=(merged7['damVMTlevels_lr_baseyr_base'] * miles_cost_lr +
                                                                 merged7['damVMTlevels_hr_baseyr_base'] * miles_cost_hr +
                                                                 merged7['damVMTlevels_b_baseyr_base'] * miles_cost_b +
                                                                 merged7['damVMTlevels_c_baseyr_base'] * miles_cost),
                                 damPHTlevel_dollar_baseyr_base=(hours_cost * (merged7['damPHTlevels_lr_e_baseyr_base'] +
                                                                               merged7['damPHTlevels_hr_e_baseyr_base'] +
                                                                               merged7['damPHTlevels_b_e_baseyr_base'] +
                                                                               merged7['damPHTlevels_c_baseyr_base']) +
                                                                 hours_wait_cost * (merged7['damPHTlevels_lr_w_baseyr_base'] +
                                                                                    merged7['damPHTlevels_hr_w_baseyr_base'] +
                                                                                    merged7['damPHTlevels_b_w_baseyr_base'])))

    # calculate vsBase metrics
    # NOTE: calculation is resilience project minus baseline
    merged7['initTripsvsBase'] = merged7['initTripslevels'] - merged7['initTripslevels_base']
    merged7['initVMTvsBase'] = merged7['initVMTlevels'] - merged7['initVMTlevels_base']
    merged7['initPHTvsBase'] = merged7['initPHTlevels'] - merged7['initPHTlevels_base']
    merged7['expTripsvsBase'] = merged7['expTripslevels'] - merged7['expTripslevels_base']
    merged7['expVMTvsBase'] = merged7['expVMTlevels'] - merged7['expVMTlevels_base']
    merged7['expPHTvsBase'] = merged7['expPHTlevels'] - merged7['expPHTlevels_base']
    if cfg['calc_transit_metrics']:
        merged7['damTripsvsBase'] = merged7['damTripslevels'] - merged7['damTripslevels_base']
        merged7['damVMTvsBase'] = merged7['damVMTlevels'] - merged7['damVMTlevels_base']
        merged7['damPHTvsBase'] = merged7['damPHTlevels'] - merged7['damPHTlevels_base']
    else:
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
    if cfg['calc_transit_metrics']:
        merged7['damTripsvsBase_baseyr'] = merged7['damTripslevels_baseyr'] - merged7['damTripslevels_baseyr_base']
        merged7['damVMTvsBase_baseyr'] = merged7['damVMTlevels_baseyr'] - merged7['damVMTlevels_baseyr_base']
        merged7['damPHTvsBase_baseyr'] = merged7['damPHTlevels_baseyr'] - merged7['damPHTlevels_baseyr_base']
    else:
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

    # calculate VMT metrics for car and bus for safety, noise, and emissions
    if cfg['calc_transit_metrics']:
        merged7['initVMTvsBase_b'] = merged7['initVMTlevels_b'] - merged7['initVMTlevels_b_base']
        merged7['initVMTvsBase_c'] = merged7['initVMTlevels_c'] - merged7['initVMTlevels_c_base']
        merged7['expVMTvsBase_b'] = merged7['expVMTlevels_b'] - merged7['expVMTlevels_b_base']
        merged7['expVMTvsBase_c'] = merged7['expVMTlevels_c'] - merged7['expVMTlevels_c_base']
        merged7['damVMTvsBase_b'] = merged7['damVMTlevels_b'] - merged7['damVMTlevels_b_base']
        merged7['damVMTvsBase_c'] = merged7['damVMTlevels_c'] - merged7['damVMTlevels_c_base']
        merged7['initVMTvsBase_b_baseyr'] = merged7['initVMTlevels_b_baseyr'] - merged7['initVMTlevels_b_baseyr_base']
        merged7['initVMTvsBase_c_baseyr'] = merged7['initVMTlevels_c_baseyr'] - merged7['initVMTlevels_c_baseyr_base']
        merged7['expVMTvsBase_b_baseyr'] = merged7['expVMTlevels_b_baseyr'] - merged7['expVMTlevels_b_baseyr_base']
        merged7['expVMTvsBase_c_baseyr'] = merged7['expVMTlevels_c_baseyr'] - merged7['expVMTlevels_c_baseyr_base']
        merged7['damVMTvsBase_b_baseyr'] = merged7['damVMTlevels_b_baseyr'] - merged7['damVMTlevels_b_baseyr_base']
        merged7['damVMTvsBase_c_baseyr'] = merged7['damVMTlevels_c_baseyr'] - merged7['damVMTlevels_c_baseyr_base']

    # calculate dollar values for Trips/VMT/PHT
    if cfg['calc_transit_metrics']:
        merged7['initTripsvsBase_dollar'] = merged7['initTripslevel_dollar'] - merged7['initTripslevel_dollar_base']
        merged7['initVMTvsBase_dollar'] = merged7['initVMTlevel_dollar'] - merged7['initVMTlevel_dollar_base']
        merged7['initPHTvsBase_dollar'] = merged7['initPHTlevel_dollar'] - merged7['initPHTlevel_dollar_base']
        merged7['expTripsvsBase_dollar'] = merged7['expTripslevel_dollar'] - merged7['expTripslevel_dollar_base']
        merged7['expVMTvsBase_dollar'] = merged7['expVMTlevel_dollar'] - merged7['expVMTlevel_dollar_base']
        merged7['expPHTvsBase_dollar'] = merged7['expPHTlevel_dollar'] - merged7['expPHTlevel_dollar_base']
        merged7['damTripsvsBase_dollar'] = merged7['damTripslevel_dollar'] - merged7['damTripslevel_dollar_base']
        merged7['damVMTvsBase_dollar'] = merged7['damVMTlevel_dollar'] - merged7['damVMTlevel_dollar_base']
        merged7['damPHTvsBase_dollar'] = merged7['damPHTlevel_dollar'] - merged7['damPHTlevel_dollar_base']
        merged7['initTripsvsBase_dollar_baseyr'] = merged7['initTripslevel_dollar_baseyr'] - merged7['initTripslevel_dollar_baseyr_base']
        merged7['initVMTvsBase_dollar_baseyr'] = merged7['initVMTlevel_dollar_baseyr'] - merged7['initVMTlevel_dollar_baseyr_base']
        merged7['initPHTvsBase_dollar_baseyr'] = merged7['initPHTlevel_dollar_baseyr'] - merged7['initPHTlevel_dollar_baseyr_base']
        merged7['expTripsvsBase_dollar_baseyr'] = merged7['expTripslevel_dollar_baseyr'] - merged7['expTripslevel_dollar_baseyr_base']
        merged7['expVMTvsBase_dollar_baseyr'] = merged7['expVMTlevel_dollar_baseyr'] - merged7['expVMTlevel_dollar_baseyr_base']
        merged7['expPHTvsBase_dollar_baseyr'] = merged7['expPHTlevel_dollar_baseyr'] - merged7['expPHTlevel_dollar_baseyr_base']
        merged7['damTripsvsBase_dollar_baseyr'] = merged7['damTripslevel_dollar_baseyr'] - merged7['damTripslevel_dollar_baseyr_base']
        merged7['damVMTvsBase_dollar_baseyr'] = merged7['damVMTlevel_dollar_baseyr'] - merged7['damVMTlevel_dollar_baseyr_base']
        merged7['damPHTvsBase_dollar_baseyr'] = merged7['damPHTlevel_dollar_baseyr'] - merged7['damPHTlevel_dollar_baseyr_base']
    else:
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

    # calculate safety, noise, and emissions benefits
    # emissions benefits are calculated using (1) a config parameter that converts VMT to an emissions metric, (2) a monetization table

    if cfg['calc_transit_metrics']:
        # calculate safety benefits compared to baseline for each period
        merged7['initSafetyvsBase'] =  safety_cost * merged7['initVMTvsBase_c'] + safety_cost_b * merged7['initVMTvsBase_b']
        merged7['expSafetyvsBase'] =  safety_cost * merged7['expVMTvsBase_c'] + safety_cost_b * merged7['expVMTvsBase_b']
        merged7['damSafetyvsBase'] =  safety_cost * merged7['damVMTvsBase_c'] + safety_cost_b * merged7['damVMTvsBase_b']
        merged7['initSafetyvsBase_baseyr'] = safety_cost * merged7['initVMTvsBase_c_baseyr'] + safety_cost_b * merged7['initVMTvsBase_b_baseyr']
        merged7['expSafetyvsBase_baseyr'] = safety_cost * merged7['expVMTvsBase_c_baseyr'] + safety_cost_b * merged7['expVMTvsBase_b_baseyr']
        merged7['damSafetyvsBase_baseyr'] = safety_cost * merged7['damVMTvsBase_c_baseyr'] + safety_cost_b * merged7['damVMTvsBase_b_baseyr']

        # calculate noise benefits compared to baseline for each period
        merged7['initNoisevsBase'] =  noise_cost * merged7['initVMTvsBase_c'] + noise_cost_b * merged7['initVMTvsBase_b']
        merged7['expNoisevsBase'] =  noise_cost * merged7['expVMTvsBase_c'] + noise_cost_b * merged7['expVMTvsBase_b']
        merged7['damNoisevsBase'] =  noise_cost * merged7['damVMTvsBase_c'] + noise_cost_b * merged7['damVMTvsBase_b']
        merged7['initNoisevsBase_baseyr'] = noise_cost * merged7['initVMTvsBase_c_baseyr'] + noise_cost_b * merged7['initVMTvsBase_b_baseyr']
        merged7['expNoisevsBase_baseyr'] = noise_cost * merged7['expVMTvsBase_c_baseyr'] + noise_cost_b * merged7['expVMTvsBase_b_baseyr']
        merged7['damNoisevsBase_baseyr'] = noise_cost * merged7['damVMTvsBase_c_baseyr'] + noise_cost_b * merged7['damVMTvsBase_b_baseyr']

        # calculate non co2 benefits compared to baseline for each period
        merged7['initNonCO2vsBase'] =  non_co2_cost * merged7['initVMTvsBase_c'] + non_co2_cost_b * merged7['initVMTvsBase_b']
        merged7['expNonCO2vsBase'] =  non_co2_cost * merged7['expVMTvsBase_c'] + non_co2_cost_b * merged7['expVMTvsBase_b']
        merged7['damNonCO2vsBase'] =  non_co2_cost * merged7['damVMTvsBase_c'] + non_co2_cost_b * merged7['damVMTvsBase_b']
        merged7['initNonCO2vsBase_baseyr'] = non_co2_cost * merged7['initVMTvsBase_c_baseyr'] + non_co2_cost_b * merged7['initVMTvsBase_b_baseyr']
        merged7['expNonCO2vsBase_baseyr'] = non_co2_cost * merged7['expVMTvsBase_c_baseyr'] + non_co2_cost_b * merged7['expVMTvsBase_b_baseyr']
        merged7['damNonCO2vsBase_baseyr'] = non_co2_cost * merged7['damVMTvsBase_c_baseyr'] + non_co2_cost_b * merged7['damVMTvsBase_b_baseyr']

        # calculate co2 benefits compared to baseline for each period
        merged7['initCO2vsBase'] =  co2_cost * merged7['initVMTvsBase_c'] + co2_cost_b * merged7['initVMTvsBase_b']
        merged7['expCO2vsBase'] =  co2_cost * merged7['expVMTvsBase_c'] + co2_cost_b * merged7['expVMTvsBase_b']
        merged7['damCO2vsBase'] =  co2_cost * merged7['damVMTvsBase_c'] + co2_cost_b * merged7['damVMTvsBase_b']
        merged7['initCO2vsBase_baseyr'] = co2_cost * merged7['initVMTvsBase_c_baseyr'] + co2_cost_b * merged7['initVMTvsBase_b_baseyr']
        merged7['expCO2vsBase_baseyr'] = co2_cost * merged7['expVMTvsBase_c_baseyr'] + co2_cost_b * merged7['expVMTvsBase_b_baseyr']
        merged7['damCO2vsBase_baseyr'] = co2_cost * merged7['damVMTvsBase_c_baseyr'] + co2_cost_b * merged7['damVMTvsBase_b_baseyr']
    else:
        # calculate safety benefits compared to baseline for each period
        merged7['initSafetyvsBase'] =  safety_cost * merged7['initVMTvsBase']
        merged7['expSafetyvsBase'] =  safety_cost * merged7['expVMTvsBase']
        merged7['damSafetyvsBase'] =  safety_cost * merged7['damVMTvsBase']
        merged7['initSafetyvsBase_baseyr'] = safety_cost * merged7['initVMTvsBase_baseyr']
        merged7['expSafetyvsBase_baseyr'] = safety_cost * merged7['expVMTvsBase_baseyr']
        merged7['damSafetyvsBase_baseyr'] = safety_cost * merged7['damVMTvsBase_baseyr']

        # calculate noise benefits compared to baseline for each period
        merged7['initNoisevsBase'] =  noise_cost * merged7['initVMTvsBase']
        merged7['expNoisevsBase'] =  noise_cost * merged7['expVMTvsBase']
        merged7['damNoisevsBase'] =  noise_cost * merged7['damVMTvsBase']
        merged7['initNoisevsBase_baseyr'] = noise_cost * merged7['initVMTvsBase_baseyr']
        merged7['expNoisevsBase_baseyr'] = noise_cost * merged7['expVMTvsBase_baseyr']
        merged7['damNoisevsBase_baseyr'] = noise_cost * merged7['damVMTvsBase_baseyr']

        # calculate non co2 benefits compared to baseline for each period
        merged7['initNonCO2vsBase'] =  non_co2_cost * merged7['initVMTvsBase']
        merged7['expNonCO2vsBase'] =  non_co2_cost * merged7['expVMTvsBase']
        merged7['damNonCO2vsBase'] =  non_co2_cost * merged7['damVMTvsBase']
        merged7['initNonCO2vsBase_baseyr'] = non_co2_cost * merged7['initVMTvsBase_baseyr']
        merged7['expNonCO2vsBase_baseyr'] = non_co2_cost * merged7['expVMTvsBase_baseyr']
        merged7['damNonCO2vsBase_baseyr'] = non_co2_cost * merged7['damVMTvsBase_baseyr']

        # calculate co2 benefits compared to baseline for each period
        merged7['initCO2vsBase'] =  co2_cost * merged7['initVMTvsBase']
        merged7['expCO2vsBase'] =  co2_cost * merged7['expVMTvsBase']
        merged7['damCO2vsBase'] =  co2_cost * merged7['damVMTvsBase']
        merged7['initCO2vsBase_baseyr'] = co2_cost * merged7['initVMTvsBase_baseyr']
        merged7['expCO2vsBase_baseyr'] = co2_cost * merged7['expVMTvsBase_baseyr']
        merged7['damCO2vsBase_baseyr'] = co2_cost * merged7['damVMTvsBase_baseyr']

    # NOTE: for clean up, set 0 for baseline scenarios to keep NaN from propagating through calculations
    merged7.loc[merged7['Resiliency Project'] == 'no', ['expSafetyvsBase', 'expNoisevsBase', 'expNonCO2vsBase', 'expCO2vsBase', 'expVMTvsBase',
                                                        'damSafetyvsBase', 'damNoisevsBase', 'damNonCO2vsBase', 'damCO2vsBase', 'damVMTvsBase',
                                                        'initSafetyvsBase', 'initNoisevsBase', 'initNonCO2vsBase', 'initCO2vsBase', 'initVMTvsBase',
                                                        'expSafetyvsBase_baseyr', 'expNoisevsBase_baseyr', 'expNonCO2vsBase_baseyr', 'expCO2vsBase_baseyr', 'expVMTvsBase_baseyr',
                                                        'damSafetyvsBase_baseyr', 'damNoisevsBase_baseyr', 'damNonCO2vsBase_baseyr', 'damCO2vsBase_baseyr', 'damVMTvsBase_baseyr',
                                                        'initSafetyvsBase_baseyr', 'initNoisevsBase_baseyr', 'initNonCO2vsBase_baseyr', 'initCO2vsBase_baseyr', 'initVMTvsBase_baseyr']] = 0

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
        co2_discount = np.zeros((end_year - start_year + 1,))
        co2_discount[0] = np.float_power(1 + co2_discount_factor, start_year - dollar_year)
        co2_discount[1:] = 1 + co2_discount_factor
        co2_discount = np.cumprod(co2_discount)

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

        # noise calculations
        initNoisevsBase_startyr = (row['initNoisevsBase_baseyr'] +
                                   start_frac * (row['initNoisevsBase'] - row['initNoisevsBase_baseyr']))
        initNoisevsBase_endyr = (row['initNoisevsBase_baseyr'] +
                                 end_frac * (row['initNoisevsBase'] - row['initNoisevsBase_baseyr']))
        initNoisevsBase = np.linspace(initNoisevsBase_startyr, initNoisevsBase_endyr, end_year - start_year + 1)
        expNoisevsBase_startyr = (row['expNoisevsBase_baseyr'] +
                                  start_frac * (row['expNoisevsBase'] - row['expNoisevsBase_baseyr']))
        expNoisevsBase_endyr = (row['expNoisevsBase_baseyr'] +
                                end_frac * (row['expNoisevsBase'] - row['expNoisevsBase_baseyr']))
        expNoisevsBase = np.linspace(expNoisevsBase_startyr, expNoisevsBase_endyr, end_year - start_year + 1)
        damNoisevsBase_startyr = (row['damNoisevsBase_baseyr'] +
                                  start_frac * (row['damNoisevsBase'] - row['damNoisevsBase_baseyr']))
        damNoisevsBase_endyr = (row['damNoisevsBase_baseyr'] +
                                end_frac * (row['damNoisevsBase'] - row['damNoisevsBase_baseyr']))
        damNoisevsBase = np.linspace(damNoisevsBase_startyr, damNoisevsBase_endyr, end_year - start_year + 1)

        temp_stage['initNoisevsBase'] = np.mean(initNoisevsBase)
        temp_stage['expNoisevsBase'] = np.mean(expNoisevsBase)
        temp_stage['damNoisevsBase'] = np.mean(damNoisevsBase)
        temp_stage['initNoise_Discounted'] = np.sum(initNoisevsBase / discount)
        temp_stage['expNoise_Discounted'] = np.sum(expNoisevsBase / discount)
        temp_stage['damNoise_Discounted'] = np.sum(damNoisevsBase / discount)

        # emissions calculations
        initNonCO2vsBase_startyr = (row['initNonCO2vsBase_baseyr'] +
                                    start_frac * (row['initNonCO2vsBase'] - row['initNonCO2vsBase_baseyr']))
        initNonCO2vsBase_endyr = (row['initNonCO2vsBase_baseyr'] +
                                  end_frac * (row['initNonCO2vsBase'] - row['initNonCO2vsBase_baseyr']))
        initNonCO2vsBase = np.linspace(initNonCO2vsBase_startyr, initNonCO2vsBase_endyr, end_year - start_year + 1)
        initCO2vsBase_startyr = (row['initCO2vsBase_baseyr'] +
                                 start_frac * (row['initCO2vsBase'] - row['initCO2vsBase_baseyr']))
        initCO2vsBase_endyr = (row['initCO2vsBase_baseyr'] +
                               end_frac * (row['initCO2vsBase'] - row['initCO2vsBase_baseyr']))
        initCO2vsBase = np.linspace(initCO2vsBase_startyr, initCO2vsBase_endyr, end_year - start_year + 1)

        expNonCO2vsBase_startyr = (row['expNonCO2vsBase_baseyr'] +
                                   start_frac * (row['expNonCO2vsBase'] - row['expNonCO2vsBase_baseyr']))
        expNonCO2vsBase_endyr = (row['expNonCO2vsBase_baseyr'] +
                                 end_frac * (row['expNonCO2vsBase'] - row['expNonCO2vsBase_baseyr']))
        expNonCO2vsBase = np.linspace(expNonCO2vsBase_startyr, expNonCO2vsBase_endyr, end_year - start_year + 1)
        expCO2vsBase_startyr = (row['expCO2vsBase_baseyr'] +
                                start_frac * (row['expCO2vsBase'] - row['expCO2vsBase_baseyr']))
        expCO2vsBase_endyr = (row['expCO2vsBase_baseyr'] +
                              end_frac * (row['expCO2vsBase'] - row['expCO2vsBase_baseyr']))
        expCO2vsBase = np.linspace(expCO2vsBase_startyr, expCO2vsBase_endyr, end_year - start_year + 1)

        damNonCO2vsBase_startyr = (row['damNonCO2vsBase_baseyr'] +
                                   start_frac * (row['damNonCO2vsBase'] - row['damNonCO2vsBase_baseyr']))
        damNonCO2vsBase_endyr = (row['damNonCO2vsBase_baseyr'] +
                                 end_frac * (row['damNonCO2vsBase'] - row['damNonCO2vsBase_baseyr']))
        damNonCO2vsBase = np.linspace(damNonCO2vsBase_startyr, damNonCO2vsBase_endyr, end_year - start_year + 1)
        damCO2vsBase_startyr = (row['damCO2vsBase_baseyr'] +
                                start_frac * (row['damCO2vsBase'] - row['damCO2vsBase_baseyr']))
        damCO2vsBase_endyr = (row['damCO2vsBase_baseyr'] +
                              end_frac * (row['damCO2vsBase'] - row['damCO2vsBase_baseyr']))
        damCO2vsBase = np.linspace(damCO2vsBase_startyr, damCO2vsBase_endyr, end_year - start_year + 1)

        temp_stage['initEmissionsvsBase'] = np.mean(initNonCO2vsBase + initCO2vsBase)
        temp_stage['expEmissionsvsBase'] = np.mean(expNonCO2vsBase + expCO2vsBase)
        temp_stage['damEmissionsvsBase'] = np.mean(damNonCO2vsBase + damCO2vsBase)
        temp_stage['initEmissions_Discounted'] = np.sum(initNonCO2vsBase / discount) + np.sum(initCO2vsBase / co2_discount)
        temp_stage['expEmissions_Discounted'] = np.sum(expNonCO2vsBase / discount) + np.sum(expCO2vsBase / co2_discount)
        temp_stage['damEmissions_Discounted'] = np.sum(damNonCO2vsBase / discount) + np.sum(damCO2vsBase / co2_discount)

        # calculate (1) discounted maintenance cost, (2) discounted project cost based on lifespan, (3) residual cost benefit
        if redeployment:
            cost_stream = np.zeros((end_year - start_year + 1,))
            cost_stream[::row['Project Lifespan']] = row['Estimated Redeployment Cost']
            cost_stream[0] = row['Estimated Project Cost']
            temp_stage['ProjectCosts_Discounted'] = np.sum(cost_stream / discount)
            residual_stream = np.zeros((end_year - start_year + 1,))
            remaining_years = row['Project Lifespan'] - (end_year - start_year + 1) % row['Project Lifespan']
            if (end_year - start_year) < row['Project Lifespan']:
                residual_stream[-1] = row['Estimated Project Cost'] * (remaining_years / row['Project Lifespan'])
            else:
                residual_stream[-1] = row['Estimated Redeployment Cost'] * (remaining_years / row['Project Lifespan'])
            temp_stage['TotalResidual_Discounted'] = np.sum(residual_stream / discount)

        else:
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

        temp_stage['Benefits_Discounted'] = (np.sum((expTripsvsBase_dollar + expVMTvsBase_dollar + expPHTvsBase_dollar
                                                     + expSafetyvsBase + expNoisevsBase + expNonCO2vsBase
                                                     - row['AssetDamagevsBase_dollar'] + damTripsvsBase_dollar
                                                     + damVMTvsBase_dollar + damPHTvsBase_dollar + damSafetyvsBase
                                                     + damNoisevsBase + damNonCO2vsBase)
                                                    * event_prob / discount) +
                                             np.sum((expCO2vsBase + damCO2vsBase)
                                                    * event_prob / co2_discount) +
                                             temp_stage['TotalResidual_Discounted'] -
                                             temp_stage['TotalMaintenanceCosts_Discounted'])
        temp_stage['ExpBenefits_Discounted'] = (np.sum((expTripsvsBase_dollar + expVMTvsBase_dollar
                                                        + expPHTvsBase_dollar + expSafetyvsBase + expNoisevsBase
                                                        + expNonCO2vsBase) * event_prob / discount) +
                                                np.sum(expCO2vsBase * event_prob / co2_discount))
        temp_stage['RepairCleanupCostSavings_Discounted'] = np.sum((0 - row['AssetDamagevsBase_dollar']) *
                                                                   event_prob / discount)
        temp_stage['DamBenefits_Discounted'] = (np.sum((damTripsvsBase_dollar + damVMTvsBase_dollar
                                                        + damPHTvsBase_dollar + damSafetyvsBase + damNoisevsBase
                                                        + damNonCO2vsBase) * event_prob / discount) +
                                                np.sum(damCO2vsBase * event_prob / co2_discount))
        temp_stage['NetBenefits_Discounted'] = temp_stage['Benefits_Discounted'] - temp_stage['ProjectCosts_Discounted']
        if temp_stage['ProjectCosts_Discounted'] == 0:
            temp_stage['BCR_Discounted'] = np.NaN
        else:
            temp_stage['BCR_Discounted'] = np.float64(temp_stage['Benefits_Discounted']) / temp_stage['ProjectCosts_Discounted']

        final_table = pd.concat([final_table, pd.DataFrame(dict(temp_stage), index=[0])], ignore_index=True)

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
    BCAnohazard = BCAnohazard.drop(labels=['Hazard Event'], axis=1)
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
                                           'expPHTlevels_base'],
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
        final_table['Benefits_Discounted'] = 0
        final_table['NetBenefits_Discounted'] = 0
        final_table['TotalNetBenefits_Discounted'] = 0

    # assign 'IDResiliencyScenario' = 0, 'Project Group' = 'None' for all baseline averages
    tableau_table = final_table.drop(['Hazard Event'], axis=1).groupby(['IDScenario',
                                                                        'ResiliencyProject',
                                                                        'ProjectName', 'Asset',
                                                                        'ResiliencyProjectAsset',
                                                                        'Year', 'EconomicScenario',
                                                                        'Exposurerecoverypath',
                                                                        'DamageRecoveryPath'],
                                                                       as_index=False, sort=False).mean()
    tableau_table.loc[tableau_table['ResiliencyProject'] == 'no', ['IDResiliencyScenario']] = 0
    tableau_table.loc[tableau_table['ResiliencyProject'] == 'no', ['Project Group']] = 'None'

    # create a Parameters table for Tableau based on CSV file in config file with cfg values joined in
    parameters_table = os.path.join(os.path.abspath(os.path.join(os.getcwd(), os.pardir)), 'config',
                                    'parameters_lookup.csv')
    logger.config("Reading in parameters file: {}".format(parameters_table))
    if not os.path.exists(parameters_table):
        logger.error("PARAMETERS LOOKUP FILE ERROR: {} could not be found".format(parameters_table))
        raise Exception("PARAMETERS LOOKUP FILE ERROR: {} could not be found".format(parameters_table))
    parameters = pd.read_csv(parameters_table,
                             usecols=['Category', 'Parameter', 'Description'],
                             converters={'Category': str, 'Parameters': str, 'Description': str})
    parameters['Value'] = np.NaN
    for index, row in parameters.iterrows():
        if row['Parameter'] not in ['socio', 'projgroup', 'elasticity', 'hazard', 'num_recov_stages', 'resil', 'event_freq_factors']:
            parameters.loc[index, 'Value'] = cfg[row['Parameter']]
        elif row['Parameter'] == 'socio':
            parameters.loc[index, 'Value'] = '; '.join(str(e) for e in tableau_table['EconomicScenario'].unique().tolist())
        elif row['Parameter'] == 'projgroup':
            parameters.loc[index, 'Value'] = '; '.join(str(e) for e in tableau_table['Project Group'].unique().tolist())
        elif row['Parameter'] == 'elasticity':
            parameters.loc[index, 'Value'] = '; '.join(str(e) for e in tableau_table['TripElasticity'].unique().tolist())
        elif row['Parameter'] == 'hazard':
            parameters.loc[index, 'Value'] = '; '.join(str(e) for e in hazard_levels['Hazard Event'].unique().tolist())
        elif row['Parameter'] == 'num_recov_stages':
            parameters.loc[index, 'Value'] = '; '.join(str(e) for e in hazard_levels['Recovery'].unique().tolist())
        elif row['Parameter'] == 'resil':
            parameters.loc[index, 'Value'] = '; '.join(str(e) for e in tableau_table['ResiliencyProject'].unique().tolist())
        elif row['Parameter'] == 'event_freq_factors':
            parameters.loc[index, 'Value'] = '; '.join(str(e) for e in tableau_table['FutureEventFrequency'].unique().tolist())

    # create a BCA table for Tableau summarizing benefits and costs when roi_analysis_type = 'BCA'
    bca_table_agg = final_table.loc[:, ['ProjectName', 'IDScenarioNoHazard', 'Hazard Event',
                                        'NetBenefits_Discounted', 'Benefits_Discounted',
                                        'BCR_Discounted']].groupby(['ProjectName', 'IDScenarioNoHazard',
                                                                    'Hazard Event'],
                                                                    as_index=False, sort=False).mean()
    bca_table_agg = bca_table_agg.drop(['Hazard Event'], axis=1).groupby(['ProjectName', 'IDScenarioNoHazard'],
                                                                         as_index=False, sort=False).sum()

    bca_table_1 = bca_table_agg.loc[:, ['ProjectName', 'IDScenarioNoHazard', 'Benefits_Discounted']]
    # normalize by the number of uncertainty scenarios (no hazard)
    bca_table_1['Benefits_Discounted'] = bca_table_1['Benefits_Discounted'] / len(bca_table_1['IDScenarioNoHazard'].unique())
    bca_table_1 = pd.melt(bca_table_1, id_vars=['ProjectName', 'IDScenarioNoHazard'], value_vars=['Benefits_Discounted'])
    # renaming IDScenarioNoHazard to IDScenario for Tableau compatibility
    bca_table_1.rename({'IDScenarioNoHazard': 'IDScenario', 'variable': 'Attribute', 'value': 'Value'}, axis='columns', inplace=True)

    bca_table_2 = tableau_table.loc[:, ['ProjectName', 'ProjectCosts_Discounted',
                                        'TotalNetBenefits_Discounted']].groupby(['ProjectName'],
                                                                                as_index=False,
                                                                                sort=False).mean()
    bca_table_2['ProjectCosts_Discounted'] = 0 - bca_table_2['ProjectCosts_Discounted']
    bca_table_2 = pd.melt(bca_table_2, id_vars=['ProjectName'], value_vars=['ProjectCosts_Discounted',
                                                                            'TotalNetBenefits_Discounted'])
    bca_table_2.rename({'variable': 'Attribute', 'value': 'Value'}, axis='columns', inplace=True)
    bca_table_2['IDScenario'] = ''

    bca_table_3 = bca_table_agg.drop(['IDScenarioNoHazard'], axis=1).groupby('ProjectName', as_index=False,
                                                                             sort=False).mean()
    bca_table_3 = pd.melt(bca_table_3, id_vars=['ProjectName'], value_vars=['NetBenefits_Discounted',
                                                                            'Benefits_Discounted',
                                                                            'BCR_Discounted'])
    bca_table_3.rename({'variable': 'Attribute', 'value': 'Value'}, axis='columns', inplace=True)
    bca_table_3['IDScenario'] = ''

    bca_table = pd.concat([bca_table_1, bca_table_2, bca_table_3], ignore_index=True)

    # if regret analysis, zero out BCA values
    if roi_analysis_type == 'Regret':
        bca_table['Value'] = 0

    tableau_file = os.path.join(output_folder, 'tableau_input_file_' + str(cfg['run_id']) + '.xlsx')
    logger.result("Tableau dashboard input table written to {}".format(tableau_file))
    with pd.ExcelWriter(tableau_file) as writer:
        # write scenario output metrics
        tableau_table.to_excel(writer, sheet_name="Scenarios", index=False,
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
                                        'damSafety_Discounted', 'initNoise_Discounted', 'expNoise_Discounted',
                                        'damNoise_Discounted', 'initEmissions_Discounted', 'expEmissions_Discounted',
                                        'damEmissions_Discounted', 'TotalMaintenanceCosts_Discounted', 'TotalResidual_Discounted'])
        # write parameter outputs
        parameters.to_excel(writer, sheet_name="Parameters", index=False)
        # write BCA outputs
        bca_table.to_excel(writer, sheet_name="BCA", index=False)

    tableau_dir = prepare_tableau_assets(tableau_file, output_folder, cfg, logger)
    logger.result("Tableau dashboard written to directory {}".format(tableau_dir))

    logger.info("Finished: recovery analysis module")


# ==============================================================================


# check ROI inputs based on ROI Analysis Type parameter
def check_roi_required_inputs(input_folder, cfg, logger):
    logger.info("Start: check_roi_required_inputs")
    is_covered = 1

    if cfg['cfg_type'] == 'config':
        model_params_file = os.path.join(input_folder, 'Model_Parameters.xlsx')
        if not os.path.exists(model_params_file):
            logger.error("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
            raise Exception("MODEL PARAMETERS FILE ERROR: {} could not be found".format(model_params_file))
        model_params = pd.read_excel(model_params_file, sheet_name='Hazards',
                                     usecols=['Hazard Event', 'Event Probability in Start Year'],
                                     converters={'Hazard Event': str, 'Event Probability in Start Year': float})
    else:  # cfg_type = 'json'
        model_params = cfg['hazards']

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
