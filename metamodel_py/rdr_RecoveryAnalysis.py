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
import geopandas as gpd
from rdr_RecoveryInit import make_hazard_levels
from rdr_supporting import check_file_exists, check_left_merge


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
    scenarios_table = check_file_exists(os.path.join(output_folder, 'uncertainty_scenarios_' + str(cfg['run_id']) + '.csv'), logger)
    extended_table = check_file_exists(os.path.join(output_folder, 'extended_scenarios_' + str(cfg['run_id']) + '.csv'), logger)
    repair_table = check_file_exists(os.path.join(output_folder, 'scenario_repair_output_' + str(cfg['run_id']) + '.csv'), logger)

    # SP or RT run type specified in config file
    # NOTE: do not currently use lost trips, extra miles, extra hours, circuitous_trips_removed fields
    # NOTE: cfg['run_id'] not used in filename for base year metrics
    base_regression_table = check_file_exists(os.path.join(input_folder,
                                                           'Metamodel_scenarios_' + cfg['aeq_run_type'] + '_baseyear.csv'),
                                              logger)
    future_regression_table = check_file_exists(os.path.join(output_folder,
                                                             'Metamodel_scenarios_' + cfg['aeq_run_type'] +
                                                             '_futureyear_' + str(cfg['run_id']) + '.csv'),
                                                logger)

    master_table = pd.read_csv(scenarios_table, converters = {'Economic': str, 'Project Group': str,
                                                 'Resiliency Project': str, 'Trip Loss Elasticity': float,
                                                 'Initial Hazard Level': int})
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
        model_params_file = check_file_exists(os.path.join(input_folder, 'Model_Parameters.xlsx'), logger)
        hazard_levels = make_hazard_levels(model_params_file, 'config', logger)
        projgroup_to_resil = pd.read_excel(model_params_file, sheet_name='ProjectGroups',
                                           converters={'Project Groups': str, 'Project ID': str})
        projgroup_to_resil = projgroup_to_resil.rename(columns={'Project ID': 'Resiliency Projects'})
    else:  # cfg_type = 'json'
        hazard_levels = make_hazard_levels(cfg, 'json', logger)
        projgroup_to_resil = cfg['projects']
        projgroup_to_resil = projgroup_to_resil.rename(columns={'Project ID': 'Resiliency Projects'})

    projgroup_to_resil = projgroup_to_resil.loc[:, ['Project Groups',
                                                    'Resiliency Projects']].drop_duplicates(ignore_index=True)

    hazard_levels = hazard_levels.loc[:, ['Hazard Level', 'HazardDim1', 'HazardDim2', 'Hazard Event',
                                          'Recovery', 'Event Probability in Start Year', 'Filename']]
    logger.debug("Size of hazard information table: {}".format(hazard_levels.shape))

    project_table = check_file_exists(os.path.join(input_folder, 'LookupTables', 'project_info.csv'), logger)
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
    projects['Estimated Project Cost'] = projects['Project Cost'].replace('[\$,]', '', regex=True).replace('', '0.0').astype(float)
    projects['Estimated Maintenance Cost'] = 0
    projects['Estimated Redeployment Cost'] = 0

    # assign maintenance and redeployment costs only if they are set to be included in config
    if maintenance:
        projects['Estimated Maintenance Cost'] = projects['Annual Maintenance Cost'].replace('[\$,]', '', regex=True).replace('', '0.0').astype(float)
    if redeployment:
        projects['Estimated Redeployment Cost'] = projects['Redeployment Cost'].replace('[\$,]', '', regex=True).replace('', '0.0').astype(float)
    
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
    ext_haz = pd.merge(extended_scenarios, hazard_levels.loc[:, ['Hazard Level', 'Hazard Event', 'Recovery']],
                       how='left', left_on='Exposure Level', right_on='Hazard Level', indicator=True)
    ext_haz = check_left_merge(ext_haz, "any", "extended scenarios", "hazards", logger)

    # merge with future_regression_output in left outer merge on:
    # 'Economic' = 'socio', 'Project Group' = 'projgroup', 'Resiliency Project' = 'resil',
    # 'Trip Loss Elasticity' = 'elasticity', 'Hazard Event' = 'hazard', 'Recovery' = 'recovery'
    ext_reg = pd.merge(ext_haz, future_regression_output, how='left',
                       left_on=['Economic', 'Project Group', 'Resiliency Project',
                                'Trip Loss Elasticity', 'Hazard Event', 'Recovery'],
                       right_on=['socio', 'projgroup', 'resil', 'elasticity', 'hazard', 'recovery'], indicator=True)
    ext_reg = check_left_merge(ext_reg, "any", "extended scenarios with hazards",
                               "future year regression", logger, "Re-run metamodel module.")

    # merge with base_regression_output in left outer merge on 'Hazard Event' = 'hazard', 'Recovery' = 'recovery'
    # NOTE: merge with base year regression outputs is only based on hazard and recovery
    logger.warning("variation in base year regression outputs is solely due to hazard event and recovery parameters")
    if cfg['calc_transit_metrics']:
        ext_reg = pd.merge(ext_reg, base_regression_output.loc[:, ['hazard', 'recovery', 'trips', 'miles', 'hours',
                                                                   'lr_trips', 'hr_trips', 'bus_trips', 'car_trips',
                                                                   'lr_miles', 'hr_miles', 'bus_miles', 'car_miles',
                                                                   'lr_hours_wait', 'hr_hours_wait', 'bus_hours_wait',
                                                                   'lr_hours_enroute', 'hr_hours_enroute',
                                                                   'bus_hours_enroute', 'car_hours']],
                           how='left', left_on=['Hazard Event', 'Recovery'], right_on=['hazard', 'recovery'],
                           suffixes=(None, "_baseyr"), indicator=True)
    else:
        ext_reg = pd.merge(ext_reg, base_regression_output.loc[:, ['hazard', 'recovery', 'trips', 'miles', 'hours']],
                           how='left', left_on=['Hazard Event', 'Recovery'], right_on=['hazard', 'recovery'],
                           suffixes=(None, "_baseyr"), indicator=True)
    ext_reg = check_left_merge(ext_reg, "any", "extended scenarios with hazards",
                               "base year regression", logger)
    ext_reg = ext_reg.drop(labels=['hazard_baseyr', 'recovery_baseyr'], axis=1)

    # calculate new columns 'initTripslevels'/'initVMTlevels'/'initPHTlevels' as
    # 'trips'/'miles'/'hours' for 'Stage Number' == 1 and 0 otherwise (and dividing by vehicle_occupancy for VMT)
    if cfg['calc_transit_metrics']:
        ext_reg['initTripslevels_lr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['lr_trips'], 0.0)
        ext_reg['initTripslevels_hr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hr_trips'], 0.0)
        ext_reg['initTripslevels_b'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['bus_trips'], 0.0)
        ext_reg['initTripslevels_c'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['car_trips'], 0.0)
        ext_reg['initVMTlevels_lr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['lr_miles'] / vehicle_occupancy_lr, 0.0)
        ext_reg['initVMTlevels_hr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hr_miles'] / vehicle_occupancy_hr, 0.0)
        ext_reg['initVMTlevels_b'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['bus_miles'] / vehicle_occupancy_b, 0.0)
        ext_reg['initVMTlevels_c'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['car_miles'] / vehicle_occupancy, 0.0)
        ext_reg['initPHTlevels_lr_w'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['lr_hours_wait'], 0.0)
        ext_reg['initPHTlevels_hr_w'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hr_hours_wait'], 0.0)
        ext_reg['initPHTlevels_b_w'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['bus_hours_wait'], 0.0)
        ext_reg['initPHTlevels_lr_e'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['lr_hours_enroute'], 0.0)
        ext_reg['initPHTlevels_hr_e'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hr_hours_enroute'], 0.0)
        ext_reg['initPHTlevels_b_e'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['bus_hours_enroute'], 0.0)
        ext_reg['initPHTlevels_c'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['car_hours'], 0.0)

        ext_reg['initTripslevels_lr_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['lr_trips_baseyr'], 0.0)
        ext_reg['initTripslevels_hr_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hr_trips_baseyr'], 0.0)
        ext_reg['initTripslevels_b_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['bus_trips_baseyr'], 0.0)
        ext_reg['initTripslevels_c_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['car_trips_baseyr'], 0.0)
        ext_reg['initVMTlevels_lr_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['lr_miles_baseyr'] / vehicle_occupancy_lr, 0.0)
        ext_reg['initVMTlevels_hr_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hr_miles_baseyr'] / vehicle_occupancy_hr, 0.0)
        ext_reg['initVMTlevels_b_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['bus_miles_baseyr'] / vehicle_occupancy_b, 0.0)
        ext_reg['initVMTlevels_c_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['car_miles_baseyr'] / vehicle_occupancy, 0.0)
        ext_reg['initPHTlevels_lr_w_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['lr_hours_wait_baseyr'], 0.0)
        ext_reg['initPHTlevels_hr_w_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hr_hours_wait_baseyr'], 0.0)
        ext_reg['initPHTlevels_b_w_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['bus_hours_wait_baseyr'], 0.0)
        ext_reg['initPHTlevels_lr_e_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['lr_hours_enroute_baseyr'], 0.0)
        ext_reg['initPHTlevels_hr_e_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hr_hours_enroute_baseyr'], 0.0)
        ext_reg['initPHTlevels_b_e_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['bus_hours_enroute_baseyr'], 0.0)
        ext_reg['initPHTlevels_c_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['car_hours_baseyr'], 0.0)

        ext_reg = ext_reg.assign(initTripslevels=(ext_reg['initTripslevels_lr'] + ext_reg['initTripslevels_hr'] +
                                                  ext_reg['initTripslevels_b'] + ext_reg['initTripslevels_c']),
                                 initVMTlevels=(ext_reg['initVMTlevels_lr'] + ext_reg['initVMTlevels_hr'] +
                                                ext_reg['initVMTlevels_b'] + ext_reg['initVMTlevels_c']),
                                 initPHTlevels=(ext_reg['initPHTlevels_lr_w'] + ext_reg['initPHTlevels_hr_w'] +
                                                ext_reg['initPHTlevels_b_w'] + ext_reg['initPHTlevels_lr_e'] +
                                                ext_reg['initPHTlevels_hr_e'] + ext_reg['initPHTlevels_b_e'] +
                                                ext_reg['initPHTlevels_c']),
                                 initTripslevels_baseyr=(ext_reg['initTripslevels_lr_baseyr'] + ext_reg['initTripslevels_hr_baseyr'] +
                                                         ext_reg['initTripslevels_b_baseyr'] + ext_reg['initTripslevels_c_baseyr']),
                                 initVMTlevels_baseyr=(ext_reg['initVMTlevels_lr_baseyr'] + ext_reg['initVMTlevels_hr_baseyr'] +
                                                       ext_reg['initVMTlevels_b_baseyr'] + ext_reg['initVMTlevels_c_baseyr']),
                                 initPHTlevels_baseyr=(ext_reg['initPHTlevels_lr_w_baseyr'] + ext_reg['initPHTlevels_hr_w_baseyr'] +
                                                       ext_reg['initPHTlevels_b_w_baseyr'] + ext_reg['initPHTlevels_lr_e_baseyr'] +
                                                       ext_reg['initPHTlevels_hr_e_baseyr'] + ext_reg['initPHTlevels_b_e_baseyr'] +
                                                       ext_reg['initPHTlevels_c_baseyr']))
    else:
        ext_reg['initTripslevels'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['trips'], 0.0)
        ext_reg['initVMTlevels'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['miles'] / vehicle_occupancy, 0.0)
        ext_reg['initPHTlevels'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hours'], 0.0)
        ext_reg['initTripslevels_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['trips_baseyr'], 0.0)
        ext_reg['initVMTlevels_baseyr'] = np.where(ext_reg['Stage Number'] == 1,
                                                   ext_reg['miles_baseyr'] / vehicle_occupancy, 0.0)
        ext_reg['initPHTlevels_baseyr'] = np.where(ext_reg['Stage Number'] == 1, ext_reg['hours_baseyr'], 0.0)

    # calculate new columns 'expTripslevels'/'expVMTlevels'/'expPHTlevels' by multiplying
    # 'Stage Duration' and 'trips'/'miles'/'hours' (and dividing by vehicle_occupancy for VMT)
    if cfg['calc_transit_metrics']:
        ext_reg = ext_reg.assign(expTripslevels_lr=ext_reg['Stage Duration'] * ext_reg['lr_trips'],
                                 expTripslevels_hr=ext_reg['Stage Duration'] * ext_reg['hr_trips'],
                                 expTripslevels_b=ext_reg['Stage Duration'] * ext_reg['bus_trips'],
                                 expTripslevels_c=ext_reg['Stage Duration'] * ext_reg['car_trips'],
                                 expVMTlevels_lr=ext_reg['Stage Duration'] * ext_reg['lr_miles']/vehicle_occupancy_lr,
                                 expVMTlevels_hr=ext_reg['Stage Duration'] * ext_reg['hr_miles']/vehicle_occupancy_hr,
                                 expVMTlevels_b=ext_reg['Stage Duration'] * ext_reg['bus_miles']/vehicle_occupancy_b,
                                 expVMTlevels_c=ext_reg['Stage Duration'] * ext_reg['car_miles']/vehicle_occupancy,
                                 expPHTlevels_lr_w=ext_reg['Stage Duration'] * ext_reg['lr_hours_wait'],
                                 expPHTlevels_hr_w=ext_reg['Stage Duration'] * ext_reg['hr_hours_wait'],
                                 expPHTlevels_b_w=ext_reg['Stage Duration'] * ext_reg['bus_hours_wait'],
                                 expPHTlevels_lr_e=ext_reg['Stage Duration'] * ext_reg['lr_hours_enroute'],
                                 expPHTlevels_hr_e=ext_reg['Stage Duration'] * ext_reg['hr_hours_enroute'],
                                 expPHTlevels_b_e=ext_reg['Stage Duration'] * ext_reg['bus_hours_enroute'],
                                 expPHTlevels_c=ext_reg['Stage Duration'] * ext_reg['car_hours'])
        ext_reg = ext_reg.assign(expTripslevels_lr_baseyr=ext_reg['Stage Duration'] * ext_reg['lr_trips_baseyr'],
                                 expTripslevels_hr_baseyr=ext_reg['Stage Duration'] * ext_reg['hr_trips_baseyr'],
                                 expTripslevels_b_baseyr=ext_reg['Stage Duration'] * ext_reg['bus_trips_baseyr'],
                                 expTripslevels_c_baseyr=ext_reg['Stage Duration'] * ext_reg['car_trips_baseyr'],
                                 expVMTlevels_lr_baseyr=ext_reg['Stage Duration'] * ext_reg['lr_miles_baseyr']/vehicle_occupancy_lr,
                                 expVMTlevels_hr_baseyr=ext_reg['Stage Duration'] * ext_reg['hr_miles_baseyr']/vehicle_occupancy_hr,
                                 expVMTlevels_b_baseyr=ext_reg['Stage Duration'] * ext_reg['bus_miles_baseyr']/vehicle_occupancy_b,
                                 expVMTlevels_c_baseyr=ext_reg['Stage Duration'] * ext_reg['car_miles_baseyr']/vehicle_occupancy,
                                 expPHTlevels_lr_w_baseyr=ext_reg['Stage Duration'] * ext_reg['lr_hours_wait_baseyr'],
                                 expPHTlevels_hr_w_baseyr=ext_reg['Stage Duration'] * ext_reg['hr_hours_wait_baseyr'],
                                 expPHTlevels_b_w_baseyr=ext_reg['Stage Duration'] * ext_reg['bus_hours_wait_baseyr'],
                                 expPHTlevels_lr_e_baseyr=ext_reg['Stage Duration'] * ext_reg['lr_hours_enroute_baseyr'],
                                 expPHTlevels_hr_e_baseyr=ext_reg['Stage Duration'] * ext_reg['hr_hours_enroute_baseyr'],
                                 expPHTlevels_b_e_baseyr=ext_reg['Stage Duration'] * ext_reg['bus_hours_enroute_baseyr'],
                                 expPHTlevels_c_baseyr=ext_reg['Stage Duration'] * ext_reg['car_hours_baseyr'])

        ext_reg = ext_reg.assign(expTripslevels=(ext_reg['expTripslevels_lr'] + ext_reg['expTripslevels_hr'] +
                                                 ext_reg['expTripslevels_b'] + ext_reg['expTripslevels_c']),
                                 expVMTlevels=(ext_reg['expVMTlevels_lr'] + ext_reg['expVMTlevels_hr'] +
                                               ext_reg['expVMTlevels_b'] + ext_reg['expVMTlevels_c']),
                                 expPHTlevels=(ext_reg['expPHTlevels_lr_w'] + ext_reg['expPHTlevels_hr_w'] +
                                               ext_reg['expPHTlevels_b_w'] + ext_reg['expPHTlevels_lr_e'] +
                                               ext_reg['expPHTlevels_hr_e'] + ext_reg['expPHTlevels_b_e'] +
                                               ext_reg['expPHTlevels_c']),
                                 expTripslevels_baseyr=(ext_reg['expTripslevels_lr_baseyr'] + ext_reg['expTripslevels_hr_baseyr'] +
                                                        ext_reg['expTripslevels_b_baseyr'] + ext_reg['expTripslevels_c_baseyr']),
                                 expVMTlevels_baseyr=(ext_reg['expVMTlevels_lr_baseyr'] + ext_reg['expVMTlevels_hr_baseyr'] +
                                                      ext_reg['expVMTlevels_b_baseyr'] + ext_reg['expVMTlevels_c_baseyr']),
                                 expPHTlevels_baseyr=(ext_reg['expPHTlevels_lr_w_baseyr'] + ext_reg['expPHTlevels_hr_w_baseyr'] +
                                                      ext_reg['expPHTlevels_b_w_baseyr'] + ext_reg['expPHTlevels_lr_e_baseyr'] +
                                                      ext_reg['expPHTlevels_hr_e_baseyr'] + ext_reg['expPHTlevels_b_e_baseyr'] +
                                                      ext_reg['expPHTlevels_c_baseyr']))
    else:
        ext_reg = ext_reg.assign(expTripslevels=ext_reg['Stage Duration'] * ext_reg['trips'],
                                 expVMTlevels=ext_reg['Stage Duration'] * ext_reg['miles']/vehicle_occupancy,
                                 expPHTlevels=ext_reg['Stage Duration'] * ext_reg['hours'])
        ext_reg = ext_reg.assign(expTripslevels_baseyr=ext_reg['Stage Duration'] * ext_reg['trips_baseyr'],
                                 expVMTlevels_baseyr=ext_reg['Stage Duration'] * ext_reg['miles_baseyr']/vehicle_occupancy,
                                 expPHTlevels_baseyr=ext_reg['Stage Duration'] * ext_reg['hours_baseyr'])

    # create table of maximum recovery stage metrics for partial repair calculation
    # using one row per project-scenario
    logger.debug("identifying maximum recovery stages for partial repair calculation")
    ext_reg['recovery_depth'] = ext_reg['Recovery'].astype(float)
    if cfg['calc_transit_metrics']:
        maximum_recovery_data = ext_reg.loc[ext_reg.reset_index().groupby(['ID-Resiliency-Scenario'])['recovery_depth'].idxmax(),
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
        maximum_recovery_data = maximum_recovery_data.rename({'lr_trips': 'initTripslevels_lr', 'hr_trips': 'initTripslevels_hr',
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
                                                        axis='columns')
    else:
        maximum_recovery_data = ext_reg.loc[ext_reg.reset_index().groupby(['ID-Resiliency-Scenario'])['recovery_depth'].idxmax(),
                                            ['ID-Resiliency-Scenario', 'trips', 'miles', 'hours',
                                             'trips_baseyr', 'miles_baseyr', 'hours_baseyr']]
        maximum_recovery_data['miles'] = maximum_recovery_data['miles'] / vehicle_occupancy
        maximum_recovery_data['miles_baseyr'] = maximum_recovery_data['miles_baseyr'] / vehicle_occupancy
        maximum_recovery_data = maximum_recovery_data.rename({'trips': 'initTripslevels', 'miles': 'initVMTlevels', 'hours': 'initPHTlevels',
                                                              'trips_baseyr': 'initTripslevels_baseyr', 'miles_baseyr': 'initVMTlevels_baseyr',
                                                              'hours_baseyr': 'initPHTlevels_baseyr'},
                                                             axis='columns')

    # consolidate extended scenarios into one row per project-scenario
    # group by 'ID-Resiliency-Scenario', sum metrics columns
    logger.debug("consolidating extended scenario snapshots into uncertainty scenarios")
    if cfg['calc_transit_metrics']:
        hazard_recession_data = ext_reg.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
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
        hazard_recession_data = ext_reg.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
                                                'initPHTlevels', 'initTripslevels_baseyr', 'initVMTlevels_baseyr',
                                                'initPHTlevels_baseyr', 'expTripslevels', 'expVMTlevels', 'expPHTlevels',
                                                'expTripslevels_baseyr', 'expVMTlevels_baseyr',
                                                'expPHTlevels_baseyr']].groupby('ID-Resiliency-Scenario', as_index=False,
                                                                                sort=False).sum()

    # calculate dollar values for Trips/VMT/PHT
    # NOTE: monetization of trips does not occur until comparing against baseline
    logger.debug("calculating dollar values for Trips/VMT/PHT metrics")
    if cfg['calc_transit_metrics']:
        hazard_recession_data = hazard_recession_data.assign(initVMTlevel_dollar=(hazard_recession_data['initVMTlevels_lr'] * miles_cost_lr +
                                                                                  hazard_recession_data['initVMTlevels_hr'] * miles_cost_hr +
                                                                                  hazard_recession_data['initVMTlevels_b'] * miles_cost_b +
                                                                                  hazard_recession_data['initVMTlevels_c'] * miles_cost),
                                                             initSafetylevel_dollar=(hazard_recession_data['initVMTlevels_b'] * safety_cost_b +
                                                                                     hazard_recession_data['initVMTlevels_c'] * safety_cost),
                                                             initNoiselevel_dollar=(hazard_recession_data['initVMTlevels_b'] * noise_cost_b +
                                                                                    hazard_recession_data['initVMTlevels_c'] * noise_cost),
                                                             initNonCO2level_dollar=(hazard_recession_data['initVMTlevels_b'] * non_co2_cost_b +
                                                                                     hazard_recession_data['initVMTlevels_c'] * non_co2_cost),
                                                             initCO2level_dollar=(hazard_recession_data['initVMTlevels_b'] * co2_cost_b +
                                                                                  hazard_recession_data['initVMTlevels_c'] * co2_cost),
                                                             initPHTlevel_dollar=(hours_cost * (hazard_recession_data['initPHTlevels_lr_e'] +
                                                                                                hazard_recession_data['initPHTlevels_hr_e'] +
                                                                                                hazard_recession_data['initPHTlevels_b_e'] +
                                                                                                hazard_recession_data['initPHTlevels_c']) +
                                                                                  hours_wait_cost * (hazard_recession_data['initPHTlevels_lr_w'] +
                                                                                                     hazard_recession_data['initPHTlevels_hr_w'] +
                                                                                                     hazard_recession_data['initPHTlevels_b_w'])),
                                                             expVMTlevel_dollar=(hazard_recession_data['expVMTlevels_lr'] * miles_cost_lr +
                                                                                 hazard_recession_data['expVMTlevels_hr'] * miles_cost_hr +
                                                                                 hazard_recession_data['expVMTlevels_b'] * miles_cost_b +
                                                                                 hazard_recession_data['expVMTlevels_c'] * miles_cost),
                                                             expSafetylevel_dollar=(hazard_recession_data['expVMTlevels_b'] * safety_cost_b +
                                                                                     hazard_recession_data['expVMTlevels_c'] * safety_cost),
                                                             expNoiselevel_dollar=(hazard_recession_data['expVMTlevels_b'] * noise_cost_b +
                                                                                    hazard_recession_data['expVMTlevels_c'] * noise_cost),
                                                             expNonCO2level_dollar=(hazard_recession_data['expVMTlevels_b'] * non_co2_cost_b +
                                                                                     hazard_recession_data['expVMTlevels_c'] * non_co2_cost),
                                                             expCO2level_dollar=(hazard_recession_data['expVMTlevels_b'] * co2_cost_b +
                                                                                  hazard_recession_data['expVMTlevels_c'] * co2_cost),
                                                             expPHTlevel_dollar=(hours_cost * (hazard_recession_data['expPHTlevels_lr_e'] +
                                                                                               hazard_recession_data['expPHTlevels_hr_e'] +
                                                                                               hazard_recession_data['expPHTlevels_b_e'] +
                                                                                               hazard_recession_data['expPHTlevels_c']) +
                                                                                 hours_wait_cost * (hazard_recession_data['expPHTlevels_lr_w'] +
                                                                                                    hazard_recession_data['expPHTlevels_hr_w'] +
                                                                                                    hazard_recession_data['expPHTlevels_b_w'])))
        hazard_recession_data = hazard_recession_data.assign(initVMTlevel_dollar_baseyr=(hazard_recession_data['initVMTlevels_lr_baseyr'] * miles_cost_lr +
                                                                                         hazard_recession_data['initVMTlevels_hr_baseyr'] * miles_cost_hr +
                                                                                         hazard_recession_data['initVMTlevels_b_baseyr'] * miles_cost_b +
                                                                                         hazard_recession_data['initVMTlevels_c_baseyr'] * miles_cost),
                                                             initSafetylevel_dollar_baseyr=(hazard_recession_data['initVMTlevels_b_baseyr'] * safety_cost_b +
                                                                                            hazard_recession_data['initVMTlevels_c_baseyr'] * safety_cost),
                                                             initNoiselevel_dollar_baseyr=(hazard_recession_data['initVMTlevels_b_baseyr'] * noise_cost_b +
                                                                                           hazard_recession_data['initVMTlevels_c_baseyr'] * noise_cost),
                                                             initNonCO2level_dollar_baseyr=(hazard_recession_data['initVMTlevels_b_baseyr'] * non_co2_cost_b +
                                                                                            hazard_recession_data['initVMTlevels_c_baseyr'] * non_co2_cost),
                                                             initCO2level_dollar_baseyr=(hazard_recession_data['initVMTlevels_b_baseyr'] * co2_cost_b +
                                                                                         hazard_recession_data['initVMTlevels_c_baseyr'] * co2_cost),
                                                             initPHTlevel_dollar_baseyr=(hours_cost * (hazard_recession_data['initPHTlevels_lr_e_baseyr'] +
                                                                                                       hazard_recession_data['initPHTlevels_hr_e_baseyr'] +
                                                                                                       hazard_recession_data['initPHTlevels_b_e_baseyr'] +
                                                                                                       hazard_recession_data['initPHTlevels_c_baseyr']) +
                                                                                         hours_wait_cost * (hazard_recession_data['initPHTlevels_lr_w_baseyr'] +
                                                                                                            hazard_recession_data['initPHTlevels_hr_w_baseyr'] +
                                                                                                            hazard_recession_data['initPHTlevels_b_w_baseyr'])),
                                                             expVMTlevel_dollar_baseyr=(hazard_recession_data['expVMTlevels_lr_baseyr'] * miles_cost_lr +
                                                                                        hazard_recession_data['expVMTlevels_hr_baseyr'] * miles_cost_hr +
                                                                                        hazard_recession_data['expVMTlevels_b_baseyr'] * miles_cost_b +
                                                                                        hazard_recession_data['expVMTlevels_c_baseyr'] * miles_cost),
                                                             expSafetylevel_dollar_baseyr=(hazard_recession_data['expVMTlevels_b_baseyr'] * safety_cost_b +
                                                                                            hazard_recession_data['expVMTlevels_c_baseyr'] * safety_cost),
                                                             expNoiselevel_dollar_baseyr=(hazard_recession_data['expVMTlevels_b_baseyr'] * noise_cost_b +
                                                                                           hazard_recession_data['expVMTlevels_c_baseyr'] * noise_cost),
                                                             expNonCO2level_dollar_baseyr=(hazard_recession_data['expVMTlevels_b_baseyr'] * non_co2_cost_b +
                                                                                            hazard_recession_data['expVMTlevels_c_baseyr'] * non_co2_cost),
                                                             expCO2level_dollar_baseyr=(hazard_recession_data['expVMTlevels_b_baseyr'] * co2_cost_b +
                                                                                         hazard_recession_data['expVMTlevels_c_baseyr'] * co2_cost),
                                                             expPHTlevel_dollar_baseyr=(hours_cost * (hazard_recession_data['expPHTlevels_lr_e_baseyr'] +
                                                                                                      hazard_recession_data['expPHTlevels_hr_e_baseyr'] +
                                                                                                      hazard_recession_data['expPHTlevels_b_e_baseyr'] +
                                                                                                      hazard_recession_data['expPHTlevels_c_baseyr']) +
                                                                                        hours_wait_cost * (hazard_recession_data['expPHTlevels_lr_w_baseyr'] +
                                                                                                           hazard_recession_data['expPHTlevels_hr_w_baseyr'] +
                                                                                                           hazard_recession_data['expPHTlevels_b_w_baseyr'])))
    else:
        hazard_recession_data = hazard_recession_data.assign(initVMTlevel_dollar=(hazard_recession_data['initVMTlevels'] *
                                                                                  miles_cost),
                                                             initSafetylevel_dollar=(hazard_recession_data['initVMTlevels'] * safety_cost),
                                                             initNoiselevel_dollar=(hazard_recession_data['initVMTlevels'] * noise_cost),
                                                             initNonCO2level_dollar=(hazard_recession_data['initVMTlevels'] * non_co2_cost),
                                                             initCO2level_dollar=(hazard_recession_data['initVMTlevels'] * co2_cost),
                                                             initPHTlevel_dollar=(hazard_recession_data['initPHTlevels'] *
                                                                                  hours_cost),
                                                             expVMTlevel_dollar=(hazard_recession_data['expVMTlevels'] *
                                                                                 miles_cost),
                                                             expSafetylevel_dollar=(hazard_recession_data['expVMTlevels'] * safety_cost),
                                                             expNoiselevel_dollar=(hazard_recession_data['expVMTlevels'] * noise_cost),
                                                             expNonCO2level_dollar=(hazard_recession_data['expVMTlevels'] * non_co2_cost),
                                                             expCO2level_dollar=(hazard_recession_data['expVMTlevels'] * co2_cost),
                                                             expPHTlevel_dollar=(hazard_recession_data['expPHTlevels'] *
                                                                                 hours_cost))
        hazard_recession_data = hazard_recession_data.assign(initVMTlevel_dollar_baseyr=(hazard_recession_data['initVMTlevels_baseyr'] *
                                                                                         miles_cost),
                                                             initSafetylevel_dollar_baseyr=(hazard_recession_data['initVMTlevels_baseyr'] * safety_cost),
                                                             initNoiselevel_dollar_baseyr=(hazard_recession_data['initVMTlevels_baseyr'] * noise_cost),
                                                             initNonCO2level_dollar_baseyr=(hazard_recession_data['initVMTlevels_baseyr'] * non_co2_cost),
                                                             initCO2level_dollar_baseyr=(hazard_recession_data['initVMTlevels_baseyr'] * co2_cost),
                                                             initPHTlevel_dollar_baseyr=(hazard_recession_data['initPHTlevels_baseyr'] *
                                                                                         hours_cost),
                                                             expVMTlevel_dollar_baseyr=(hazard_recession_data['expVMTlevels_baseyr'] *
                                                                                        miles_cost),
                                                             expSafetylevel_dollar_baseyr=(hazard_recession_data['expVMTlevels_baseyr'] * safety_cost),
                                                             expNoiselevel_dollar_baseyr=(hazard_recession_data['expVMTlevels_baseyr'] * noise_cost),
                                                             expNonCO2level_dollar_baseyr=(hazard_recession_data['expVMTlevels_baseyr'] * non_co2_cost),
                                                             expCO2level_dollar_baseyr=(hazard_recession_data['expVMTlevels_baseyr'] * co2_cost),
                                                             expPHTlevel_dollar_baseyr=(hazard_recession_data['expPHTlevels_baseyr'] *
                                                                                        hours_cost))

    # merge with master_table on 'ID-Resiliency-Scenario'
    df_add_rec = pd.merge(master_table, hazard_recession_data, how='left', on='ID-Resiliency-Scenario', indicator=True)
    df_add_rec = check_left_merge(df_add_rec, "all", "uncertainty scenarios", "hazard recession", logger)

    logger.debug("pulling in resilience project and hazard event information")
    # pull in columns for 'Asset', 'Estimated Project Cost', 'Project Lifespan', 'Estimated Maintenance Cost', and 'Estimated Redeployment Cost' from project_list
    df_add_proj = pd.merge(df_add_rec, project_list.loc[:, ['Project ID', 'Project Name', 'Asset', 'Estimated Project Cost',
                                                            'Project Lifespan', 'Estimated Maintenance Cost',
                                                            'Estimated Redeployment Cost']],
                           how='left', left_on='Resiliency Project', right_on='Project ID', indicator=True)
    df_add_proj = check_left_merge(df_add_proj, "all", "uncertainty scenarios", "resilience project", logger)
    # create column 'ResiliencyProjectAsset'
    df_add_proj = df_add_proj.assign(ResiliencyProjectAsset=df_add_proj['Resiliency Project'] + ' - ' + df_add_proj['Asset'])

    # pull in columns for 'HazardDim1', 'HazardDim2', and 'Event Probability' from hazard_levels
    df_add_haz = pd.merge(df_add_proj, hazard_levels.loc[:, ['Hazard Level', 'HazardDim1', 'HazardDim2', 'Hazard Event',
                                                             'Event Probability in Start Year']],
                          how='left', left_on='Initial Hazard Level', right_on='Hazard Level', indicator=True)
    df_add_haz = check_left_merge(df_add_haz, "all", "uncertainty scenarios", "hazard event", logger)
    df_add_haz = df_add_haz.rename({'Event Probability in Start Year': 'Event Probability'}, axis='columns')
    # create column 'Year'
    df_add_haz['Year'] = str(start_year) + "-" + str(end_year)

    df_add_haz = df_add_haz.drop(labels=['Initial Hazard Level', 'Project ID', 'Hazard Level'], axis=1)

    # merge with repair_data in left outer merge on 'ID-Resiliency-Scenario'
    # pull in 'damage_repair', 'total_repair', 'repair_time', and 'damage' for baseline and project scenarios
    logger.debug("pulling in repair cost and time data")
    df_add_rep = pd.merge(df_add_haz, repair_data.loc[:, ['ID-Resiliency-Scenario', 'baseline_damage_repair',
                                                          'project_damage_repair', 'baseline_total_repair',
                                                          'project_total_repair', 'baseline_repair_time',
                                                          'project_repair_time', 'baseline_damage',
                                                          'project_damage']],
                          how='left', on='ID-Resiliency-Scenario', indicator=True)
    # NOTE: this number will be > 0 for now since baseline scenarios are not found in repair_data table
    logger.debug("Note that below number of not matched scenarios will be > 0 due to baseline scenarios")
    df_add_rep = check_left_merge(df_add_rep, "all", "uncertainty scenarios", "damage and repair", logger)

    # create damage and repair cost/time columns across all scenarios
    # NOTE: fields are missing values for baseline scenarios
    df_add_rep['damage_repair'] = np.where(df_add_rep['Resiliency Project'] == 'no', df_add_rep['baseline_damage_repair'],
                                           df_add_rep['project_damage_repair'])
    df_add_rep['total_repair'] = np.where(df_add_rep['Resiliency Project'] == 'no', df_add_rep['baseline_total_repair'],
                                          df_add_rep['project_total_repair'])
    df_add_rep['repair_time'] = np.where(df_add_rep['Resiliency Project'] == 'no', df_add_rep['baseline_repair_time'],
                                         df_add_rep['project_repair_time'])
    df_add_rep['Damage (%)'] = np.where(df_add_rep['Resiliency Project'] == 'no', df_add_rep['baseline_damage'],
                                        df_add_rep['project_damage'])
    df_add_rep = df_add_rep.drop(labels=['project_damage_repair', 'project_total_repair', 'project_repair_time', 'project_damage'],
                                 axis=1)
    # rename "baseline_" damage and repair measures to "_base"
    df_add_rep = df_add_rep.rename({'baseline_damage_repair': 'damage_repair_base', 'baseline_total_repair': 'total_repair_base',
                                    'baseline_repair_time': 'repair_time_base', 'baseline_damage': 'damage_base'},
                                   axis='columns')

    # merge with maximum recovery stage metrics for partial repair calculation
    logger.debug("pulling in metrics for maximum recovery stage as proxy for full repaired state")
    df_dam = pd.merge(df_add_rep, maximum_recovery_data, how='left', on='ID-Resiliency-Scenario',
                      suffixes=[None, '_max'], indicator=True)
    df_dam = check_left_merge(df_dam, "all", "uncertainty scenarios", "maximum recovery stage", logger)

    # create column 'DamageRecoveryPath'
    logger.warning("column 'DamageRecoveryPath' assumes linear damage recovery across repair time")
    df_dam['DamageRecoveryPath'] = '1,0'
    logger.warning(("columns 'AssetDamagelevels' and 'AssetDamagelevel_dollar' are missing values for baseline scenarios"))
    # create column 'AssetDamagelevels' - set to NaN for baseline scenarios and 'Damage (%)' for resilience project scenarios
    df_dam['AssetDamagelevels'] = np.where(df_dam['Resiliency Project'] == 'no', np.nan, df_dam['Damage (%)'])
    # create column 'AssetDamagelevel_dollar' - set to NaN for baseline scenarios and 'total_repair' for resilience project scenarios
    df_dam['AssetDamagelevel_dollar'] = np.where(df_dam['Resiliency Project'] == 'no', np.nan, df_dam['total_repair'])

    # calculate metrics for damage repair period
    # NOTE: fields are missing values for baseline scenarios
    dam_repair_time = np.where(df_dam['repair_time'] == 0, df_dam['repair_time_base'], df_dam['repair_time'])
    if cfg['calc_transit_metrics']:
        df_dam['damTripslevels_lr'] = 0.5 * (df_dam['initTripslevels_lr'] + df_dam['initTripslevels_lr_max']) * dam_repair_time
        df_dam['damTripslevels_hr'] = 0.5 * (df_dam['initTripslevels_hr'] + df_dam['initTripslevels_hr_max']) * dam_repair_time
        df_dam['damTripslevels_b'] = 0.5 * (df_dam['initTripslevels_b'] + df_dam['initTripslevels_b_max']) * dam_repair_time
        df_dam['damTripslevels_c'] = 0.5 * (df_dam['initTripslevels_c'] + df_dam['initTripslevels_c_max']) * dam_repair_time
        df_dam['damVMTlevels_lr'] = 0.5 * (df_dam['initVMTlevels_lr'] + df_dam['initVMTlevels_lr_max']) * dam_repair_time
        df_dam['damVMTlevels_hr'] = 0.5 * (df_dam['initVMTlevels_hr'] + df_dam['initVMTlevels_hr_max']) * dam_repair_time
        df_dam['damVMTlevels_b'] = 0.5 * (df_dam['initVMTlevels_b'] + df_dam['initVMTlevels_b_max']) * dam_repair_time
        df_dam['damVMTlevels_c'] = 0.5 * (df_dam['initVMTlevels_c'] + df_dam['initVMTlevels_c_max']) * dam_repair_time
        df_dam['damPHTlevels_lr_w'] = 0.5 * (df_dam['initPHTlevels_lr_w'] + df_dam['initPHTlevels_lr_w_max']) * dam_repair_time
        df_dam['damPHTlevels_hr_w'] = 0.5 * (df_dam['initPHTlevels_hr_w'] + df_dam['initPHTlevels_hr_w_max']) * dam_repair_time
        df_dam['damPHTlevels_b_w'] = 0.5 * (df_dam['initPHTlevels_b_w'] + df_dam['initPHTlevels_b_w_max']) * dam_repair_time
        df_dam['damPHTlevels_lr_e'] = 0.5 * (df_dam['initPHTlevels_lr_e'] + df_dam['initPHTlevels_lr_e_max']) * dam_repair_time
        df_dam['damPHTlevels_hr_e'] = 0.5 * (df_dam['initPHTlevels_hr_e'] + df_dam['initPHTlevels_hr_e_max']) * dam_repair_time
        df_dam['damPHTlevels_b_e'] = 0.5 * (df_dam['initPHTlevels_b_e'] + df_dam['initPHTlevels_b_e_max']) * dam_repair_time
        df_dam['damPHTlevels_c'] = 0.5 * (df_dam['initPHTlevels_c'] + df_dam['initPHTlevels_c_max']) * dam_repair_time
        df_dam['damTripslevels_lr_baseyr'] = 0.5 * (df_dam['initTripslevels_lr_baseyr'] +
                                                    df_dam['initTripslevels_lr_baseyr_max']) * dam_repair_time
        df_dam['damTripslevels_hr_baseyr'] = 0.5 * (df_dam['initTripslevels_hr_baseyr'] +
                                                    df_dam['initTripslevels_hr_baseyr_max']) * dam_repair_time
        df_dam['damTripslevels_b_baseyr'] = 0.5 * (df_dam['initTripslevels_b_baseyr'] +
                                                   df_dam['initTripslevels_b_baseyr_max']) * dam_repair_time
        df_dam['damTripslevels_c_baseyr'] = 0.5 * (df_dam['initTripslevels_c_baseyr'] +
                                                   df_dam['initTripslevels_c_baseyr_max']) * dam_repair_time
        df_dam['damVMTlevels_lr_baseyr'] = 0.5 * (df_dam['initVMTlevels_lr_baseyr'] +
                                                  df_dam['initVMTlevels_lr_baseyr_max']) * dam_repair_time
        df_dam['damVMTlevels_hr_baseyr'] = 0.5 * (df_dam['initVMTlevels_hr_baseyr'] +
                                                  df_dam['initVMTlevels_hr_baseyr_max']) * dam_repair_time
        df_dam['damVMTlevels_b_baseyr'] = 0.5 * (df_dam['initVMTlevels_b_baseyr'] +
                                                 df_dam['initVMTlevels_b_baseyr_max']) * dam_repair_time
        df_dam['damVMTlevels_c_baseyr'] = 0.5 * (df_dam['initVMTlevels_c_baseyr'] +
                                                 df_dam['initVMTlevels_c_baseyr_max']) * dam_repair_time
        df_dam['damPHTlevels_lr_w_baseyr'] = 0.5 * (df_dam['initPHTlevels_lr_w_baseyr'] +
                                                    df_dam['initPHTlevels_lr_w_baseyr_max']) * dam_repair_time
        df_dam['damPHTlevels_hr_w_baseyr'] = 0.5 * (df_dam['initPHTlevels_hr_w_baseyr'] +
                                                    df_dam['initPHTlevels_hr_w_baseyr_max']) * dam_repair_time
        df_dam['damPHTlevels_b_w_baseyr'] = 0.5 * (df_dam['initPHTlevels_b_w_baseyr'] +
                                                   df_dam['initPHTlevels_b_w_baseyr_max']) * dam_repair_time
        df_dam['damPHTlevels_lr_e_baseyr'] = 0.5 * (df_dam['initPHTlevels_lr_e_baseyr'] +
                                                    df_dam['initPHTlevels_lr_e_baseyr_max']) * dam_repair_time
        df_dam['damPHTlevels_hr_e_baseyr'] = 0.5 * (df_dam['initPHTlevels_hr_e_baseyr'] +
                                                    df_dam['initPHTlevels_hr_e_baseyr_max']) * dam_repair_time
        df_dam['damPHTlevels_b_e_baseyr'] = 0.5 * (df_dam['initPHTlevels_b_e_baseyr'] +
                                                   df_dam['initPHTlevels_b_e_baseyr_max']) * dam_repair_time
        df_dam['damPHTlevels_c_baseyr'] = 0.5 * (df_dam['initPHTlevels_c_baseyr'] +
                                                 df_dam['initPHTlevels_c_baseyr_max']) * dam_repair_time
        df_dam = df_dam.assign(damTripslevels=(df_dam['damTripslevels_lr'] + df_dam['damTripslevels_hr'] +
                                               df_dam['damTripslevels_b'] + df_dam['damTripslevels_c']),
                               damVMTlevels=(df_dam['damVMTlevels_lr'] + df_dam['damVMTlevels_hr'] +
                                             df_dam['damVMTlevels_b'] + df_dam['damVMTlevels_c']),
                               damPHTlevels=(df_dam['damPHTlevels_lr_w'] + df_dam['damPHTlevels_hr_w'] +
                                             df_dam['damPHTlevels_b_w'] + df_dam['damPHTlevels_lr_e'] +
                                             df_dam['damPHTlevels_hr_e'] + df_dam['damPHTlevels_b_e'] +
                                             df_dam['damPHTlevels_c']),
                               damTripslevels_baseyr=(df_dam['damTripslevels_lr_baseyr'] + df_dam['damTripslevels_hr_baseyr'] +
                                                      df_dam['damTripslevels_b_baseyr'] + df_dam['damTripslevels_c_baseyr']),
                               damVMTlevels_baseyr=(df_dam['damVMTlevels_lr_baseyr'] + df_dam['damVMTlevels_hr_baseyr'] +
                                                    df_dam['damVMTlevels_b_baseyr'] + df_dam['damVMTlevels_c_baseyr']),
                               damPHTlevels_baseyr=(df_dam['damPHTlevels_lr_w_baseyr'] + df_dam['damPHTlevels_hr_w_baseyr'] +
                                                    df_dam['damPHTlevels_b_w_baseyr'] + df_dam['damPHTlevels_lr_e_baseyr'] +
                                                    df_dam['damPHTlevels_hr_e_baseyr'] + df_dam['damPHTlevels_b_e_baseyr'] +
                                                    df_dam['damPHTlevels_c_baseyr']))
        df_dam = df_dam.assign(damVMTlevel_dollar=(df_dam['damVMTlevels_lr'] * miles_cost_lr +
                                                   df_dam['damVMTlevels_hr'] * miles_cost_hr +
                                                   df_dam['damVMTlevels_b'] * miles_cost_b +
                                                   df_dam['damVMTlevels_c'] * miles_cost),
                               damSafetylevel_dollar=(df_dam['damVMTlevels_b'] * safety_cost_b +
                                                      df_dam['damVMTlevels_c'] * safety_cost),
                               damNoiselevel_dollar=(df_dam['damVMTlevels_b'] * noise_cost_b +
                                                     df_dam['damVMTlevels_c'] * noise_cost),
                               damNonCO2level_dollar=(df_dam['damVMTlevels_b'] * non_co2_cost_b +
                                                      df_dam['damVMTlevels_c'] * non_co2_cost),
                               damCO2level_dollar=(df_dam['damVMTlevels_b'] * co2_cost_b +
                                                   df_dam['damVMTlevels_c'] * co2_cost),
                               damPHTlevel_dollar=(hours_cost * (df_dam['damPHTlevels_lr_e'] +
                                                                 df_dam['damPHTlevels_hr_e'] +
                                                                 df_dam['damPHTlevels_b_e'] +
                                                                 df_dam['damPHTlevels_c']) +
                                                   hours_wait_cost * (df_dam['damPHTlevels_lr_w'] +
                                                                      df_dam['damPHTlevels_hr_w'] +
                                                                      df_dam['damPHTlevels_b_w'])),
                               damVMTlevel_dollar_baseyr=(df_dam['damVMTlevels_lr_baseyr'] * miles_cost_lr +
                                                          df_dam['damVMTlevels_hr_baseyr'] * miles_cost_hr +
                                                          df_dam['damVMTlevels_b_baseyr'] * miles_cost_b +
                                                          df_dam['damVMTlevels_c_baseyr'] * miles_cost),
                               damSafetylevel_dollar_baseyr=(df_dam['damVMTlevels_b_baseyr'] * safety_cost_b +
                                                             df_dam['damVMTlevels_c_baseyr'] * safety_cost),
                               damNoiselevel_dollar_baseyr=(df_dam['damVMTlevels_b_baseyr'] * noise_cost_b +
                                                            df_dam['damVMTlevels_c_baseyr'] * noise_cost),
                               damNonCO2level_dollar_baseyr=(df_dam['damVMTlevels_b_baseyr'] * non_co2_cost_b +
                                                             df_dam['damVMTlevels_c_baseyr'] * non_co2_cost),
                               damCO2level_dollar_baseyr=(df_dam['damVMTlevels_b_baseyr'] * co2_cost_b +
                                                          df_dam['damVMTlevels_c_baseyr'] * co2_cost),
                               damPHTlevel_dollar_baseyr=(hours_cost * (df_dam['damPHTlevels_lr_e_baseyr'] +
                                                                        df_dam['damPHTlevels_hr_e_baseyr'] +
                                                                        df_dam['damPHTlevels_b_e_baseyr'] +
                                                                        df_dam['damPHTlevels_c_baseyr']) +
                                                          hours_wait_cost * (df_dam['damPHTlevels_lr_w_baseyr'] +
                                                                             df_dam['damPHTlevels_hr_w_baseyr'] +
                                                                             df_dam['damPHTlevels_b_w_baseyr'])))
    else:
        df_dam['damTripslevels'] = 0.5 * (df_dam['initTripslevels'] + df_dam['initTripslevels_max']) * dam_repair_time
        df_dam['damVMTlevels'] = 0.5 * (df_dam['initVMTlevels'] + df_dam['initVMTlevels_max']) * dam_repair_time
        df_dam['damPHTlevels'] = 0.5 * (df_dam['initPHTlevels'] + df_dam['initPHTlevels_max']) * dam_repair_time
        df_dam['damTripslevels_baseyr'] = 0.5 * (df_dam['initTripslevels_baseyr'] +
                                                 df_dam['initTripslevels_baseyr_max']) * dam_repair_time
        df_dam['damVMTlevels_baseyr'] = 0.5 * (df_dam['initVMTlevels_baseyr'] +
                                               df_dam['initVMTlevels_baseyr_max']) * dam_repair_time
        df_dam['damPHTlevels_baseyr'] = 0.5 * (df_dam['initPHTlevels_baseyr'] +
                                               df_dam['initPHTlevels_baseyr_max']) * dam_repair_time
        df_dam = df_dam.assign(damVMTlevel_dollar=df_dam['damVMTlevels'] * miles_cost,
                               damSafetylevel_dollar=df_dam['damVMTlevels'] * safety_cost,
                               damNoiselevel_dollar=df_dam['damVMTlevels'] * noise_cost,
                               damNonCO2level_dollar=df_dam['damVMTlevels'] * non_co2_cost,
                               damCO2level_dollar=df_dam['damVMTlevels'] * co2_cost,
                               damPHTlevel_dollar=df_dam['damPHTlevels'] * hours_cost,
                               damVMTlevel_dollar_baseyr=df_dam['damVMTlevels_baseyr'] * miles_cost,
                               damSafetylevel_dollar_baseyr=df_dam['damVMTlevels_baseyr'] * safety_cost,
                               damNoiselevel_dollar_baseyr=df_dam['damVMTlevels_baseyr'] * noise_cost,
                               damNonCO2level_dollar_baseyr=df_dam['damVMTlevels_baseyr'] * non_co2_cost,
                               damCO2level_dollar_baseyr=df_dam['damVMTlevels_baseyr'] * co2_cost,
                               damPHTlevel_dollar_baseyr=df_dam['damPHTlevels_baseyr'] * hours_cost)

    # use 'ID-Resiliency-Scenario-Baseline' to join to other baseline scenario metrics
    # NOTE: currently using project-level max metrics instead of baseline max metrics to calculate baseline dam metrics since not including _max columns below
    if cfg['calc_transit_metrics']:
        df_base = pd.merge(df_dam, df_dam.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
                                                  'initPHTlevels', 'initTripslevels_baseyr', 'initVMTlevels_baseyr',
                                                  'initPHTlevels_baseyr', 'expTripslevels', 'expVMTlevels',
                                                  'expPHTlevels', 'expTripslevels_baseyr', 'expVMTlevels_baseyr',
                                                  'expPHTlevels_baseyr', 'initVMTlevel_dollar',
                                                  'initSafetylevel_dollar', 'initNoiselevel_dollar',
                                                  'initNonCO2level_dollar', 'initCO2level_dollar',
                                                  'initPHTlevel_dollar', 'initVMTlevel_dollar_baseyr',
                                                  'initSafetylevel_dollar_baseyr', 'initNoiselevel_dollar_baseyr',
                                                  'initNonCO2level_dollar_baseyr', 'initCO2level_dollar_baseyr',
                                                  'initPHTlevel_dollar_baseyr', 'expVMTlevel_dollar',
                                                  'expSafetylevel_dollar', 'expNoiselevel_dollar',
                                                  'expNonCO2level_dollar', 'expCO2level_dollar',
                                                  'expPHTlevel_dollar', 'expVMTlevel_dollar_baseyr',
                                                  'expSafetylevel_dollar_baseyr', 'expNoiselevel_dollar_baseyr',
                                                  'expNonCO2level_dollar_baseyr', 'expCO2level_dollar_baseyr',
                                                  'expPHTlevel_dollar_baseyr', 'initTripslevels_lr', 'initTripslevels_hr',
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
        df_base = pd.merge(df_dam, df_dam.loc[:, ['ID-Resiliency-Scenario', 'initTripslevels', 'initVMTlevels',
                                                  'initPHTlevels', 'initTripslevels_baseyr', 'initVMTlevels_baseyr',
                                                  'initPHTlevels_baseyr', 'expTripslevels', 'expVMTlevels',
                                                  'expPHTlevels', 'expTripslevels_baseyr', 'expVMTlevels_baseyr',
                                                  'expPHTlevels_baseyr']],
                           how='left', left_on='ID-Resiliency-Scenario-Baseline', right_on='ID-Resiliency-Scenario',
                           suffixes=[None, '_base'], indicator=True)
    df_base = check_left_merge(df_base, "all", "uncertainty scenarios", "baseline scenario", logger)

    # calculate metrics for damage repair period for baseline
    # NOTE: fields are missing values for baseline scenarios
    if cfg['calc_transit_metrics']:
        df_base['damTripslevels_lr_base'] = 0.5 * (df_base['initTripslevels_lr_base'] + df_base['initTripslevels_lr_max']) * df_base['repair_time_base']
        df_base['damTripslevels_hr_base'] = 0.5 * (df_base['initTripslevels_hr_base'] + df_base['initTripslevels_hr_max']) * df_base['repair_time_base']
        df_base['damTripslevels_b_base'] = 0.5 * (df_base['initTripslevels_b_base'] + df_base['initTripslevels_b_max']) * df_base['repair_time_base']
        df_base['damTripslevels_c_base'] = 0.5 * (df_base['initTripslevels_c_base'] + df_base['initTripslevels_c_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_lr_base'] = 0.5 * (df_base['initVMTlevels_lr_base'] + df_base['initVMTlevels_lr_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_hr_base'] = 0.5 * (df_base['initVMTlevels_hr_base'] + df_base['initVMTlevels_hr_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_b_base'] = 0.5 * (df_base['initVMTlevels_b_base'] + df_base['initVMTlevels_b_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_c_base'] = 0.5 * (df_base['initVMTlevels_c_base'] + df_base['initVMTlevels_c_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_lr_w_base'] = 0.5 * (df_base['initPHTlevels_lr_w_base'] + df_base['initPHTlevels_lr_w_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_hr_w_base'] = 0.5 * (df_base['initPHTlevels_hr_w_base'] + df_base['initPHTlevels_hr_w_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_b_w_base'] = 0.5 * (df_base['initPHTlevels_b_w_base'] + df_base['initPHTlevels_b_w_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_lr_e_base'] = 0.5 * (df_base['initPHTlevels_lr_e_base'] + df_base['initPHTlevels_lr_e_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_hr_e_base'] = 0.5 * (df_base['initPHTlevels_hr_e_base'] + df_base['initPHTlevels_hr_e_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_b_e_base'] = 0.5 * (df_base['initPHTlevels_b_e_base'] + df_base['initPHTlevels_b_e_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_c_base'] = 0.5 * (df_base['initPHTlevels_c_base'] + df_base['initPHTlevels_c_max']) * df_base['repair_time_base']
        df_base['damTripslevels_lr_baseyr_base'] = 0.5 * (df_base['initTripslevels_lr_baseyr_base'] +
                                                   df_base['initTripslevels_lr_baseyr_max']) * df_base['repair_time_base']
        df_base['damTripslevels_hr_baseyr_base'] = 0.5 * (df_base['initTripslevels_hr_baseyr_base'] +
                                                   df_base['initTripslevels_hr_baseyr_max']) * df_base['repair_time_base']
        df_base['damTripslevels_b_baseyr_base'] = 0.5 * (df_base['initTripslevels_b_baseyr_base'] +
                                                  df_base['initTripslevels_b_baseyr_max']) * df_base['repair_time_base']
        df_base['damTripslevels_c_baseyr_base'] = 0.5 * (df_base['initTripslevels_c_baseyr_base'] +
                                                  df_base['initTripslevels_c_baseyr_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_lr_baseyr_base'] = 0.5 * (df_base['initVMTlevels_lr_baseyr_base'] +
                                                 df_base['initVMTlevels_lr_baseyr_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_hr_baseyr_base'] = 0.5 * (df_base['initVMTlevels_hr_baseyr_base'] +
                                                 df_base['initVMTlevels_hr_baseyr_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_b_baseyr_base'] = 0.5 * (df_base['initVMTlevels_b_baseyr_base'] +
                                                df_base['initVMTlevels_b_baseyr_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_c_baseyr_base'] = 0.5 * (df_base['initVMTlevels_c_baseyr_base'] +
                                                df_base['initVMTlevels_c_baseyr_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_lr_w_baseyr_base'] = 0.5 * (df_base['initPHTlevels_lr_w_baseyr_base'] +
                                                   df_base['initPHTlevels_lr_w_baseyr_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_hr_w_baseyr_base'] = 0.5 * (df_base['initPHTlevels_hr_w_baseyr_base'] +
                                                   df_base['initPHTlevels_hr_w_baseyr_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_b_w_baseyr_base'] = 0.5 * (df_base['initPHTlevels_b_w_baseyr_base'] +
                                                  df_base['initPHTlevels_b_w_baseyr_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_lr_e_baseyr_base'] = 0.5 * (df_base['initPHTlevels_lr_e_baseyr_base'] +
                                                   df_base['initPHTlevels_lr_e_baseyr_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_hr_e_baseyr_base'] = 0.5 * (df_base['initPHTlevels_hr_e_baseyr_base'] +
                                                   df_base['initPHTlevels_hr_e_baseyr_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_b_e_baseyr_base'] = 0.5 * (df_base['initPHTlevels_b_e_baseyr_base'] +
                                                  df_base['initPHTlevels_b_e_baseyr_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_c_baseyr_base'] = 0.5 * (df_base['initPHTlevels_c_baseyr_base'] +
                                                df_base['initPHTlevels_c_baseyr_max']) * df_base['repair_time_base']
        df_base = df_base.assign(damTripslevels_base=(df_base['damTripslevels_lr_base'] + df_base['damTripslevels_hr_base'] +
                                                      df_base['damTripslevels_b_base'] + df_base['damTripslevels_c_base']),
                                 damVMTlevels_base=(df_base['damVMTlevels_lr_base'] + df_base['damVMTlevels_hr_base'] +
                                                    df_base['damVMTlevels_b_base'] + df_base['damVMTlevels_c_base']),
                                 damPHTlevels_base=(df_base['damPHTlevels_lr_w_base'] + df_base['damPHTlevels_hr_w_base'] +
                                                    df_base['damPHTlevels_b_w_base'] + df_base['damPHTlevels_lr_e_base'] +
                                                    df_base['damPHTlevels_hr_e_base'] + df_base['damPHTlevels_b_e_base'] +
                                                    df_base['damPHTlevels_c_base']),
                                 damTripslevels_baseyr_base=(df_base['damTripslevels_lr_baseyr_base'] + df_base['damTripslevels_hr_baseyr_base'] +
                                                             df_base['damTripslevels_b_baseyr_base'] + df_base['damTripslevels_c_baseyr_base']),
                                 damVMTlevels_baseyr_base=(df_base['damVMTlevels_lr_baseyr_base'] + df_base['damVMTlevels_hr_baseyr_base'] +
                                                           df_base['damVMTlevels_b_baseyr_base'] + df_base['damVMTlevels_c_baseyr_base']),
                                 damPHTlevels_baseyr_base=(df_base['damPHTlevels_lr_w_baseyr_base'] + df_base['damPHTlevels_hr_w_baseyr_base'] +
                                                           df_base['damPHTlevels_b_w_baseyr_base'] + df_base['damPHTlevels_lr_e_baseyr_base'] +
                                                           df_base['damPHTlevels_hr_e_baseyr_base'] + df_base['damPHTlevels_b_e_baseyr_base'] +
                                                           df_base['damPHTlevels_c_baseyr_base']))
        df_base = df_base.assign(damVMTlevel_dollar_base=(df_base['damVMTlevels_lr_base'] * miles_cost_lr +
                                                          df_base['damVMTlevels_hr_base'] * miles_cost_hr +
                                                          df_base['damVMTlevels_b_base'] * miles_cost_b +
                                                          df_base['damVMTlevels_c_base'] * miles_cost),
                                 damSafetylevel_dollar_base=(df_base['damVMTlevels_b_base'] * safety_cost_b +
                                                             df_base['damVMTlevels_c_base'] * safety_cost),
                                 damNoiselevel_dollar_base=(df_base['damVMTlevels_b_base'] * noise_cost_b +
                                                            df_base['damVMTlevels_c_base'] * noise_cost),
                                 damNonCO2level_dollar_base=(df_base['damVMTlevels_b_base'] * non_co2_cost_b +
                                                             df_base['damVMTlevels_c_base'] * non_co2_cost),
                                 damCO2level_dollar_base=(df_base['damVMTlevels_b_base'] * co2_cost_b +
                                                          df_base['damVMTlevels_c_base'] * co2_cost),
                                 damPHTlevel_dollar_base=(hours_cost * (df_base['damPHTlevels_lr_e_base'] +
                                                                        df_base['damPHTlevels_hr_e_base'] +
                                                                        df_base['damPHTlevels_b_e_base'] +
                                                                        df_base['damPHTlevels_c_base']) +
                                                          hours_wait_cost * (df_base['damPHTlevels_lr_w_base'] +
                                                                             df_base['damPHTlevels_hr_w_base'] +
                                                                             df_base['damPHTlevels_b_w_base'])),
                                 damVMTlevel_dollar_baseyr_base=(df_base['damVMTlevels_lr_baseyr_base'] * miles_cost_lr +
                                                                 df_base['damVMTlevels_hr_baseyr_base'] * miles_cost_hr +
                                                                 df_base['damVMTlevels_b_baseyr_base'] * miles_cost_b +
                                                                 df_base['damVMTlevels_c_baseyr_base'] * miles_cost),
                                 damSafetylevel_dollar_baseyr_base=(df_base['damVMTlevels_b_baseyr_base'] * safety_cost_b +
                                                                    df_base['damVMTlevels_c_baseyr_base'] * safety_cost),
                                 damNoiselevel_dollar_baseyr_base=(df_base['damVMTlevels_b_baseyr_base'] * noise_cost_b +
                                                                   df_base['damVMTlevels_c_baseyr_base'] * noise_cost),
                                 damNonCO2level_dollar_baseyr_base=(df_base['damVMTlevels_b_baseyr_base'] * non_co2_cost_b +
                                                                    df_base['damVMTlevels_c_baseyr_base'] * non_co2_cost),
                                 damCO2level_dollar_baseyr_base=(df_base['damVMTlevels_b_baseyr_base'] * co2_cost_b +
                                                                 df_base['damVMTlevels_c_baseyr_base'] * co2_cost),
                                 damPHTlevel_dollar_baseyr_base=(hours_cost * (df_base['damPHTlevels_lr_e_baseyr_base'] +
                                                                               df_base['damPHTlevels_hr_e_baseyr_base'] +
                                                                               df_base['damPHTlevels_b_e_baseyr_base'] +
                                                                               df_base['damPHTlevels_c_baseyr_base']) +
                                                                 hours_wait_cost * (df_base['damPHTlevels_lr_w_baseyr_base'] +
                                                                                    df_base['damPHTlevels_hr_w_baseyr_base'] +
                                                                                    df_base['damPHTlevels_b_w_baseyr_base'])))
    else:
        df_base['damTripslevels_base'] = 0.5 * (df_base['initTripslevels_base'] + df_base['initTripslevels_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_base'] = 0.5 * (df_base['initVMTlevels_base'] + df_base['initVMTlevels_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_base'] = 0.5 * (df_base['initPHTlevels_base'] + df_base['initPHTlevels_max']) * df_base['repair_time_base']
        df_base['damTripslevels_baseyr_base'] = 0.5 * (df_base['initTripslevels_baseyr_base'] + df_base['initTripslevels_baseyr_max']) * df_base['repair_time_base']
        df_base['damVMTlevels_baseyr_base'] = 0.5 * (df_base['initVMTlevels_baseyr_base'] + df_base['initVMTlevels_baseyr_max']) * df_base['repair_time_base']
        df_base['damPHTlevels_baseyr_base'] = 0.5 * (df_base['initPHTlevels_baseyr_base'] + df_base['initPHTlevels_baseyr_max']) * df_base['repair_time_base']

    # calculate vsBase metrics
    # NOTE: calculation is resilience project minus baseline
    df_base['initTripsvsBase'] = df_base['initTripslevels'] - df_base['initTripslevels_base']
    df_base['initVMTvsBase'] = df_base['initVMTlevels'] - df_base['initVMTlevels_base']
    df_base['initPHTvsBase'] = df_base['initPHTlevels'] - df_base['initPHTlevels_base']
    df_base['expTripsvsBase'] = df_base['expTripslevels'] - df_base['expTripslevels_base']
    df_base['expVMTvsBase'] = df_base['expVMTlevels'] - df_base['expVMTlevels_base']
    df_base['expPHTvsBase'] = df_base['expPHTlevels'] - df_base['expPHTlevels_base']
    df_base['damTripsvsBase'] = df_base['damTripslevels'] - df_base['damTripslevels_base']
    df_base['damVMTvsBase'] = df_base['damVMTlevels'] - df_base['damVMTlevels_base']
    df_base['damPHTvsBase'] = df_base['damPHTlevels'] - df_base['damPHTlevels_base']
    df_base['initTripsvsBase_baseyr'] = df_base['initTripslevels_baseyr'] - df_base['initTripslevels_baseyr_base']
    df_base['initVMTvsBase_baseyr'] = df_base['initVMTlevels_baseyr'] - df_base['initVMTlevels_baseyr_base']
    df_base['initPHTvsBase_baseyr'] = df_base['initPHTlevels_baseyr'] - df_base['initPHTlevels_baseyr_base']
    df_base['expTripsvsBase_baseyr'] = df_base['expTripslevels_baseyr'] - df_base['expTripslevels_baseyr_base']
    df_base['expVMTvsBase_baseyr'] = df_base['expVMTlevels_baseyr'] - df_base['expVMTlevels_baseyr_base']
    df_base['expPHTvsBase_baseyr'] = df_base['expPHTlevels_baseyr'] - df_base['expPHTlevels_baseyr_base']
    df_base['damTripsvsBase_baseyr'] = df_base['damTripslevels_baseyr'] - df_base['damTripslevels_baseyr_base']
    df_base['damVMTvsBase_baseyr'] = df_base['damVMTlevels_baseyr'] - df_base['damVMTlevels_baseyr_base']
    df_base['damPHTvsBase_baseyr'] = df_base['damPHTlevels_baseyr'] - df_base['damPHTlevels_baseyr_base']

    # calculate dollar values for Trips/VMT/PHT
    # calculate safety, noise, and emissions benefits
    # NOTE: Trips monetization is calculated here only as change from baseline
    if cfg['calc_transit_metrics']:
        df_base['initTripsvsBase_dollar'] = ((0.5 *
                                              (((df_base['initPHTlevels_lr_w_base'] * hours_wait_cost + df_base['initPHTlevels_lr_e_base'] * hours_cost) /
                                                df_base['initTripslevels_lr_base']).fillna(0) -
                                               ((df_base['initPHTlevels_lr_w'] * hours_wait_cost + df_base['initPHTlevels_lr_e'] * hours_cost) /
                                                df_base['initTripslevels_lr']).fillna(0) + transit_fare) *
                                              (df_base['initTripslevels_lr'] - df_base['initTripslevels_lr_base'])) +
                                             (0.5 *
                                              (((df_base['initPHTlevels_hr_w_base'] * hours_wait_cost + df_base['initPHTlevels_hr_e_base'] * hours_cost) /
                                                df_base['initTripslevels_hr_base']).fillna(0) -
                                               ((df_base['initPHTlevels_hr_w'] * hours_wait_cost + df_base['initPHTlevels_hr_e'] * hours_cost) /
                                                df_base['initTripslevels_hr']).fillna(0) + transit_fare) *
                                              (df_base['initTripslevels_hr'] - df_base['initTripslevels_hr_base'])) +
                                             (0.5 *
                                              (((df_base['initPHTlevels_b_w_base'] * hours_wait_cost + df_base['initPHTlevels_b_e_base'] * hours_cost) /
                                                df_base['initTripslevels_b_base']).fillna(0) -
                                               ((df_base['initPHTlevels_b_w'] * hours_wait_cost + df_base['initPHTlevels_b_e'] * hours_cost) /
                                                df_base['initTripslevels_b']).fillna(0) + transit_fare) *
                                              (df_base['initTripslevels_b'] - df_base['initTripslevels_b_base'])) +
                                             (0.5 *
                                              ((df_base['initPHTlevels_c_base'] * hours_cost /
                                                df_base['initTripslevels_c_base']).fillna(0) -
                                               (df_base['initPHTlevels_c'] * hours_cost /
                                                df_base['initTripslevels_c']).fillna(0)) *
                                              (df_base['initTripslevels_c'] - df_base['initTripslevels_c_base'])))
        df_base['initVMTvsBase_dollar'] = df_base['initVMTlevel_dollar'] - df_base['initVMTlevel_dollar_base']
        df_base['initSafetyvsBase'] = df_base['initSafetylevel_dollar'] - df_base['initSafetylevel_dollar_base']
        df_base['initNoisevsBase'] = df_base['initNoiselevel_dollar'] - df_base['initNoiselevel_dollar_base']
        df_base['initNonCO2vsBase'] = df_base['initNonCO2level_dollar'] - df_base['initNonCO2level_dollar_base']
        df_base['initCO2vsBase'] = df_base['initCO2level_dollar'] - df_base['initCO2level_dollar_base']
        df_base['initPHTvsBase_dollar'] = df_base['initPHTlevel_dollar'] - df_base['initPHTlevel_dollar_base']
        df_base['expTripsvsBase_dollar'] = ((0.5 *
                                             (((df_base['expPHTlevels_lr_w_base'] * hours_wait_cost + df_base['expPHTlevels_lr_e_base'] * hours_cost) /
                                               df_base['expTripslevels_lr_base']).fillna(0) -
                                              ((df_base['expPHTlevels_lr_w'] * hours_wait_cost + df_base['expPHTlevels_lr_e'] * hours_cost) /
                                               df_base['expTripslevels_lr']).fillna(0) + transit_fare) *
                                             (df_base['expTripslevels_lr'] - df_base['expTripslevels_lr_base'])) +
                                            (0.5 *
                                             (((df_base['expPHTlevels_hr_w_base'] * hours_wait_cost + df_base['expPHTlevels_hr_e_base'] * hours_cost) /
                                               df_base['expTripslevels_hr_base']).fillna(0) -
                                              ((df_base['expPHTlevels_hr_w'] * hours_wait_cost + df_base['expPHTlevels_hr_e'] * hours_cost) /
                                               df_base['expTripslevels_hr']).fillna(0) + transit_fare) *
                                             (df_base['expTripslevels_hr'] - df_base['expTripslevels_hr_base'])) +
                                            (0.5 *
                                             (((df_base['expPHTlevels_b_w_base'] * hours_wait_cost + df_base['expPHTlevels_b_e_base'] * hours_cost) /
                                               df_base['expTripslevels_b_base']).fillna(0) -
                                              ((df_base['expPHTlevels_b_w'] * hours_wait_cost + df_base['expPHTlevels_b_e'] * hours_cost) /
                                               df_base['expTripslevels_b']).fillna(0) + transit_fare) *
                                             (df_base['expTripslevels_b'] - df_base['expTripslevels_b_base'])) +
                                            (0.5 *
                                             ((df_base['expPHTlevels_c_base'] * hours_cost /
                                               df_base['expTripslevels_c_base']).fillna(0) -
                                              (df_base['expPHTlevels_c'] * hours_cost /
                                               df_base['expTripslevels_c']).fillna(0)) *
                                             (df_base['expTripslevels_c'] - df_base['expTripslevels_c_base'])))
        df_base['expVMTvsBase_dollar'] = df_base['expVMTlevel_dollar'] - df_base['expVMTlevel_dollar_base']
        df_base['expSafetyvsBase'] = df_base['expSafetylevel_dollar'] - df_base['expSafetylevel_dollar_base']
        df_base['expNoisevsBase'] = df_base['expNoiselevel_dollar'] - df_base['expNoiselevel_dollar_base']
        df_base['expNonCO2vsBase'] = df_base['expNonCO2level_dollar'] - df_base['expNonCO2level_dollar_base']
        df_base['expCO2vsBase'] = df_base['expCO2level_dollar'] - df_base['expCO2level_dollar_base']
        df_base['expPHTvsBase_dollar'] = df_base['expPHTlevel_dollar'] - df_base['expPHTlevel_dollar_base']
        df_base['damTripsvsBase_dollar'] = ((0.5 *
                                             (((df_base['damPHTlevels_lr_w_base'] * hours_wait_cost + df_base['damPHTlevels_lr_e_base'] * hours_cost) /
                                               df_base['damTripslevels_lr_base']).fillna(0) -
                                              ((df_base['damPHTlevels_lr_w'] * hours_wait_cost + df_base['damPHTlevels_lr_e'] * hours_cost) /
                                               df_base['damTripslevels_lr']).fillna(0) + transit_fare) *
                                             (df_base['damTripslevels_lr'] - df_base['damTripslevels_lr_base'])) +
                                            (0.5 *
                                             (((df_base['damPHTlevels_hr_w_base'] * hours_wait_cost + df_base['damPHTlevels_hr_e_base'] * hours_cost) /
                                               df_base['damTripslevels_hr_base']).fillna(0) -
                                              ((df_base['damPHTlevels_hr_w'] * hours_wait_cost + df_base['damPHTlevels_hr_e'] * hours_cost) /
                                               df_base['damTripslevels_hr']).fillna(0) + transit_fare) *
                                             (df_base['damTripslevels_hr'] - df_base['damTripslevels_hr_base'])) +
                                            (0.5 *
                                             (((df_base['damPHTlevels_b_w_base'] * hours_wait_cost + df_base['damPHTlevels_b_e_base'] * hours_cost) /
                                               df_base['damTripslevels_b_base']).fillna(0) -
                                              ((df_base['damPHTlevels_b_w'] * hours_wait_cost + df_base['damPHTlevels_b_e'] * hours_cost) /
                                               df_base['damTripslevels_b']).fillna(0) + transit_fare) *
                                             (df_base['damTripslevels_b'] - df_base['damTripslevels_b_base'])) +
                                            (0.5 *
                                             ((df_base['damPHTlevels_c_base'] * hours_cost /
                                               df_base['damTripslevels_c_base']).fillna(0) -
                                              (df_base['damPHTlevels_c'] * hours_cost /
                                               df_base['damTripslevels_c']).fillna(0)) *
                                             (df_base['damTripslevels_c'] - df_base['damTripslevels_c_base'])))
        df_base['damVMTvsBase_dollar'] = df_base['damVMTlevel_dollar'] - df_base['damVMTlevel_dollar_base']
        df_base['damSafetyvsBase'] = df_base['damSafetylevel_dollar'] - df_base['damSafetylevel_dollar_base']
        df_base['damNoisevsBase'] = df_base['damNoiselevel_dollar'] - df_base['damNoiselevel_dollar_base']
        df_base['damNonCO2vsBase'] = df_base['damNonCO2level_dollar'] - df_base['damNonCO2level_dollar_base']
        df_base['damCO2vsBase'] = df_base['damCO2level_dollar'] - df_base['damCO2level_dollar_base']
        df_base['damPHTvsBase_dollar'] = df_base['damPHTlevel_dollar'] - df_base['damPHTlevel_dollar_base']
        df_base['initTripsvsBase_dollar_baseyr'] = ((0.5 *
                                                     (((df_base['initPHTlevels_lr_w_baseyr_base'] * hours_wait_cost + df_base['initPHTlevels_lr_e_baseyr_base'] * hours_cost) /
                                                       df_base['initTripslevels_lr_baseyr_base']).fillna(0) -
                                                      ((df_base['initPHTlevels_lr_w_baseyr'] * hours_wait_cost + df_base['initPHTlevels_lr_e_baseyr'] * hours_cost) /
                                                       df_base['initTripslevels_lr_baseyr']).fillna(0) + transit_fare) *
                                                     (df_base['initTripslevels_lr_baseyr'] - df_base['initTripslevels_lr_baseyr_base'])) +
                                                    (0.5 *
                                                     (((df_base['initPHTlevels_hr_w_baseyr_base'] * hours_wait_cost + df_base['initPHTlevels_hr_e_baseyr_base'] * hours_cost) /
                                                       df_base['initTripslevels_hr_baseyr_base']).fillna(0) -
                                                      ((df_base['initPHTlevels_hr_w_baseyr'] * hours_wait_cost + df_base['initPHTlevels_hr_e_baseyr'] * hours_cost) /
                                                       df_base['initTripslevels_hr_baseyr']).fillna(0) + transit_fare) *
                                                     (df_base['initTripslevels_hr_baseyr'] - df_base['initTripslevels_hr_baseyr_base'])) +
                                                    (0.5 *
                                                     (((df_base['initPHTlevels_b_w_baseyr_base'] * hours_wait_cost + df_base['initPHTlevels_b_e_baseyr_base'] * hours_cost) /
                                                       df_base['initTripslevels_b_baseyr_base']).fillna(0) -
                                                      ((df_base['initPHTlevels_b_w_baseyr'] * hours_wait_cost + df_base['initPHTlevels_b_e_baseyr'] * hours_cost) /
                                                       df_base['initTripslevels_b_baseyr']).fillna(0) + transit_fare) *
                                                     (df_base['initTripslevels_b_baseyr'] - df_base['initTripslevels_b_baseyr_base'])) +
                                                    (0.5 *
                                                     ((df_base['initPHTlevels_c_baseyr_base'] * hours_cost /
                                                       df_base['initTripslevels_c_baseyr_base']).fillna(0) -
                                                      (df_base['initPHTlevels_c_baseyr'] * hours_cost /
                                                       df_base['initTripslevels_c_baseyr']).fillna(0)) *
                                                     (df_base['initTripslevels_c_baseyr'] - df_base['initTripslevels_c_baseyr_base'])))
        df_base['initVMTvsBase_dollar_baseyr'] = df_base['initVMTlevel_dollar_baseyr'] - df_base['initVMTlevel_dollar_baseyr_base']
        df_base['initSafetyvsBase_baseyr'] = df_base['initSafetylevel_dollar_baseyr'] - df_base['initSafetylevel_dollar_baseyr_base']
        df_base['initNoisevsBase_baseyr'] = df_base['initNoiselevel_dollar_baseyr'] - df_base['initNoiselevel_dollar_baseyr_base']
        df_base['initNonCO2vsBase_baseyr'] = df_base['initNonCO2level_dollar_baseyr'] - df_base['initNonCO2level_dollar_baseyr_base']
        df_base['initCO2vsBase_baseyr'] = df_base['initCO2level_dollar_baseyr'] - df_base['initCO2level_dollar_base']
        df_base['initPHTvsBase_dollar_baseyr'] = df_base['initPHTlevel_dollar_baseyr'] - df_base['initPHTlevel_dollar_baseyr_base']
        df_base['expTripsvsBase_dollar_baseyr'] = ((0.5 *
                                                    (((df_base['expPHTlevels_lr_w_baseyr_base'] * hours_wait_cost + df_base['expPHTlevels_lr_e_baseyr_base'] * hours_cost) /
                                                      df_base['expTripslevels_lr_baseyr_base']).fillna(0) -
                                                     ((df_base['expPHTlevels_lr_w_baseyr'] * hours_wait_cost + df_base['expPHTlevels_lr_e_baseyr'] * hours_cost) /
                                                      df_base['expTripslevels_lr_baseyr']).fillna(0) + transit_fare) *
                                                    (df_base['expTripslevels_lr_baseyr'] - df_base['expTripslevels_lr_baseyr_base'])) +
                                                   (0.5 *
                                                    (((df_base['expPHTlevels_hr_w_baseyr_base'] * hours_wait_cost + df_base['expPHTlevels_hr_e_baseyr_base'] * hours_cost) /
                                                      df_base['expTripslevels_hr_baseyr_base']).fillna(0) -
                                                     ((df_base['expPHTlevels_hr_w_baseyr'] * hours_wait_cost + df_base['expPHTlevels_hr_e_baseyr'] * hours_cost) /
                                                      df_base['expTripslevels_hr_baseyr']).fillna(0) + transit_fare) *
                                                    (df_base['expTripslevels_hr_baseyr'] - df_base['expTripslevels_hr_baseyr_base'])) +
                                                   (0.5 *
                                                    (((df_base['expPHTlevels_b_w_baseyr_base'] * hours_wait_cost + df_base['expPHTlevels_b_e_baseyr_base'] * hours_cost) /
                                                      df_base['expTripslevels_b_baseyr_base']).fillna(0) -
                                                     ((df_base['expPHTlevels_b_w_baseyr'] * hours_wait_cost + df_base['expPHTlevels_b_e_baseyr'] * hours_cost) /
                                                      df_base['expTripslevels_b_baseyr']).fillna(0) + transit_fare) *
                                                    (df_base['expTripslevels_b_baseyr'] - df_base['expTripslevels_b_baseyr_base'])) +
                                                   (0.5 *
                                                    ((df_base['expPHTlevels_c_baseyr_base'] * hours_cost /
                                                      df_base['expTripslevels_c_baseyr_base']).fillna(0) -
                                                     (df_base['expPHTlevels_c_baseyr'] * hours_cost /
                                                      df_base['expTripslevels_c_baseyr']).fillna(0)) *
                                                    (df_base['expTripslevels_c_baseyr'] - df_base['expTripslevels_c_baseyr_base'])))
        df_base['expVMTvsBase_dollar_baseyr'] = df_base['expVMTlevel_dollar_baseyr'] - df_base['expVMTlevel_dollar_baseyr_base']
        df_base['expSafetyvsBase_baseyr'] = df_base['expSafetylevel_dollar_baseyr'] - df_base['expSafetylevel_dollar_baseyr_base']
        df_base['expNoisevsBase_baseyr'] = df_base['expNoiselevel_dollar_baseyr'] - df_base['expNoiselevel_dollar_baseyr_base']
        df_base['expNonCO2vsBase_baseyr'] = df_base['expNonCO2level_dollar_baseyr'] - df_base['expNonCO2level_dollar_baseyr_base']
        df_base['expCO2vsBase_baseyr'] = df_base['expCO2level_dollar_baseyr'] - df_base['expCO2level_dollar_base']
        df_base['expPHTvsBase_dollar_baseyr'] = df_base['expPHTlevel_dollar_baseyr'] - df_base['expPHTlevel_dollar_baseyr_base']
        df_base['damTripsvsBase_dollar_baseyr'] = ((0.5 *
                                                    (((df_base['damPHTlevels_lr_w_baseyr_base'] * hours_wait_cost + df_base['damPHTlevels_lr_e_baseyr_base'] * hours_cost) /
                                                      df_base['damTripslevels_lr_baseyr_base']).fillna(0) -
                                                     ((df_base['damPHTlevels_lr_w_baseyr'] * hours_wait_cost + df_base['damPHTlevels_lr_e_baseyr'] * hours_cost) /
                                                      df_base['damTripslevels_lr_baseyr']).fillna(0) + transit_fare) *
                                                    (df_base['damTripslevels_lr_baseyr'] - df_base['damTripslevels_lr_baseyr_base'])) +
                                                   (0.5 *
                                                    (((df_base['damPHTlevels_hr_w_baseyr_base'] * hours_wait_cost + df_base['damPHTlevels_hr_e_baseyr_base'] * hours_cost) /
                                                      df_base['damTripslevels_hr_baseyr_base']).fillna(0) -
                                                     ((df_base['damPHTlevels_hr_w_baseyr'] * hours_wait_cost + df_base['damPHTlevels_hr_e_baseyr'] * hours_cost) /
                                                      df_base['damTripslevels_hr_baseyr']).fillna(0) + transit_fare) *
                                                    (df_base['damTripslevels_hr_baseyr'] - df_base['damTripslevels_hr_baseyr_base'])) +
                                                   (0.5 *
                                                    (((df_base['damPHTlevels_b_w_baseyr_base'] * hours_wait_cost + df_base['damPHTlevels_b_e_baseyr_base'] * hours_cost) /
                                                      df_base['damTripslevels_b_baseyr_base']).fillna(0) -
                                                     ((df_base['damPHTlevels_b_w_baseyr'] * hours_wait_cost + df_base['damPHTlevels_b_e_baseyr'] * hours_cost) /
                                                      df_base['damTripslevels_b_baseyr']).fillna(0) + transit_fare) *
                                                    (df_base['damTripslevels_b_baseyr'] - df_base['damTripslevels_b_baseyr_base'])) +
                                                   (0.5 *
                                                    ((df_base['damPHTlevels_c_baseyr_base'] * hours_cost /
                                                      df_base['damTripslevels_c_baseyr_base']).fillna(0) -
                                                     (df_base['damPHTlevels_c_baseyr'] * hours_cost /
                                                      df_base['damTripslevels_c_baseyr']).fillna(0)) *
                                                    (df_base['damTripslevels_c_baseyr'] - df_base['damTripslevels_c_baseyr_base'])))
        df_base['damVMTvsBase_dollar_baseyr'] = df_base['damVMTlevel_dollar_baseyr'] - df_base['damVMTlevel_dollar_baseyr_base']
        df_base['damSafetyvsBase_baseyr'] = df_base['damSafetylevel_dollar_baseyr'] - df_base['damSafetylevel_dollar_baseyr_base']
        df_base['damNoisevsBase_baseyr'] = df_base['damNoiselevel_dollar_baseyr'] - df_base['damNoiselevel_dollar_baseyr_base']
        df_base['damNonCO2vsBase_baseyr'] = df_base['damNonCO2level_dollar_baseyr'] - df_base['damNonCO2level_dollar_baseyr_base']
        df_base['damCO2vsBase_baseyr'] = df_base['damCO2level_dollar_baseyr'] - df_base['damCO2level_dollar_base']
        df_base['damPHTvsBase_dollar_baseyr'] = df_base['damPHTlevel_dollar_baseyr'] - df_base['damPHTlevel_dollar_baseyr_base']
    else:
        df_base = df_base.assign(initTripsvsBase_dollar=(0.5 *
                                                         ((df_base['initPHTlevels_base'] * hours_cost /
                                                           df_base['initTripslevels_base']).fillna(0) -
                                                          (df_base['initPHTlevels'] * hours_cost /
                                                           df_base['initTripslevels']).fillna(0)) *
                                                         (df_base['initTripslevels'] - df_base['initTripslevels_base'])),
                                 initVMTvsBase_dollar=df_base['initVMTvsBase'] * miles_cost,
                                 initSafetyvsBase=df_base['initVMTvsBase'] * safety_cost,
                                 initNoisevsBase=df_base['initVMTvsBase'] * noise_cost,
                                 initNonCO2vsBase=df_base['initVMTvsBase'] * non_co2_cost,
                                 initCO2vsBase=df_base['initVMTvsBase'] * co2_cost,
                                 initPHTvsBase_dollar=df_base['initPHTvsBase'] * hours_cost,
                                 expTripsvsBase_dollar=(0.5 *
                                                        ((df_base['expPHTlevels_base'] * hours_cost /
                                                          df_base['expTripslevels_base']).fillna(0) -
                                                         (df_base['expPHTlevels'] * hours_cost /
                                                          df_base['expTripslevels']).fillna(0)) *
                                                        (df_base['expTripslevels'] - df_base['expTripslevels_base'])),
                                 expVMTvsBase_dollar=df_base['expVMTvsBase'] * miles_cost,
                                 expSafetyvsBase=df_base['expVMTvsBase'] * safety_cost,
                                 expNoisevsBase=df_base['expVMTvsBase'] * noise_cost,
                                 expNonCO2vsBase=df_base['expVMTvsBase'] * non_co2_cost,
                                 expCO2vsBase=df_base['expVMTvsBase'] * co2_cost,
                                 expPHTvsBase_dollar=df_base['expPHTvsBase'] * hours_cost,
                                 damTripsvsBase_dollar=(0.5 *
                                                        ((df_base['damPHTlevels_base'] * hours_cost /
                                                          df_base['damTripslevels_base']).fillna(0) -
                                                         (df_base['damPHTlevels'] * hours_cost /
                                                          df_base['damTripslevels']).fillna(0)) *
                                                        (df_base['damTripslevels'] - df_base['damTripslevels_base'])),
                                 damVMTvsBase_dollar=df_base['damVMTvsBase'] * miles_cost,
                                 damSafetyvsBase=df_base['damVMTvsBase'] * safety_cost,
                                 damNoisevsBase=df_base['damVMTvsBase'] * noise_cost,
                                 damNonCO2vsBase=df_base['damVMTvsBase'] * non_co2_cost,
                                 damCO2vsBase=df_base['damVMTvsBase'] * co2_cost,
                                 damPHTvsBase_dollar=df_base['damPHTvsBase'] * hours_cost)
        df_base = df_base.assign(initTripsvsBase_dollar_baseyr=(0.5 *
                                                                ((df_base['initPHTlevels_baseyr_base'] * hours_cost /
                                                                  df_base['initTripslevels_baseyr_base']).fillna(0) -
                                                                 (df_base['initPHTlevels_baseyr'] * hours_cost /
                                                                  df_base['initTripslevels_baseyr']).fillna(0)) *
                                                                (df_base['initTripslevels_baseyr'] - df_base['initTripslevels_baseyr_base'])),
                                 initVMTvsBase_dollar_baseyr=df_base['initVMTvsBase_baseyr'] * miles_cost,
                                 initSafetyvsBase_baseyr=df_base['initVMTvsBase_baseyr'] * safety_cost,
                                 initNoisevsBase_baseyr=df_base['initVMTvsBase_baseyr'] * noise_cost,
                                 initNonCO2vsBase_baseyr=df_base['initVMTvsBase_baseyr'] * non_co2_cost,
                                 initCO2vsBase_baseyr=df_base['initVMTvsBase_baseyr'] * co2_cost,
                                 initPHTvsBase_dollar_baseyr=df_base['initPHTvsBase_baseyr'] * hours_cost,
                                 expTripsvsBase_dollar_baseyr=(0.5 *
                                                               ((df_base['expPHTlevels_baseyr_base'] * hours_cost /
                                                                 df_base['expTripslevels_baseyr_base']).fillna(0) -
                                                                (df_base['expPHTlevels_baseyr'] * hours_cost /
                                                                 df_base['expTripslevels_baseyr']).fillna(0)) *
                                                               (df_base['expTripslevels_baseyr'] - df_base['expTripslevels_baseyr_base'])),
                                 expVMTvsBase_dollar_baseyr=df_base['expVMTvsBase_baseyr'] * miles_cost,
                                 expSafetyvsBase_baseyr=df_base['expVMTvsBase_baseyr'] * safety_cost,
                                 expNoisevsBase_baseyr=df_base['expVMTvsBase_baseyr'] * noise_cost,
                                 expNonCO2vsBase_baseyr=df_base['expVMTvsBase_baseyr'] * non_co2_cost,
                                 expCO2vsBase_baseyr=df_base['expVMTvsBase_baseyr'] * co2_cost,
                                 expPHTvsBase_dollar_baseyr=df_base['expPHTvsBase_baseyr'] * hours_cost,
                                 damTripsvsBase_dollar_baseyr=(0.5 *
                                                               ((df_base['damPHTlevels_baseyr_base'] * hours_cost /
                                                                 df_base['damTripslevels_baseyr_base']).fillna(0) -
                                                                (df_base['damPHTlevels_baseyr'] * hours_cost /
                                                                 df_base['damTripslevels_baseyr']).fillna(0)) *
                                                               (df_base['damTripslevels_baseyr'] - df_base['damTripslevels_baseyr_base'])),
                                 damVMTvsBase_dollar_baseyr=df_base['damVMTvsBase_baseyr'] * miles_cost,
                                 damSafetyvsBase_baseyr=df_base['damVMTvsBase_baseyr'] * safety_cost,
                                 damNoisevsBase_baseyr=df_base['damVMTvsBase_baseyr'] * noise_cost,
                                 damNonCO2vsBase_baseyr=df_base['damVMTvsBase_baseyr'] * non_co2_cost,
                                 damCO2vsBase_baseyr=df_base['damVMTvsBase_baseyr'] * co2_cost,
                                 damPHTvsBase_dollar_baseyr=df_base['damPHTvsBase_baseyr'] * hours_cost)

    # NOTE: for clean up, set 0 for baseline scenarios to keep NaN from propagating through calculations
    df_base.loc[df_base['Resiliency Project'] == 'no', ['expTripsvsBase_dollar', 'expVMTvsBase_dollar',
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
    df_base['AssetDamagevsBase'] = np.where(df_base['Resiliency Project'] == 'no', 0, df_base['Damage (%)'] - df_base['damage_base'])
    # create column 'AssetDamagevsBase_dollar' - set to 0 for baseline and 'total_repair' - 'total_repair_base' for resiliency scenarios
    # NOTE: for clean up, set 0 for baseline scenarios to keep NaN from propagating through calculations
    df_base['AssetDamagevsBase_dollar'] = np.where(df_base['Resiliency Project'] == 'no', 0,
                                                   df_base['total_repair'] - df_base['total_repair_base'])
    # NOTE: for clean up, set 0 for baseline scenarios to keep NaN from propagating through calculations
    df_base.loc[df_base['Resiliency Project'] == 'no', ['expSafetyvsBase', 'expNoisevsBase', 'expNonCO2vsBase', 'expCO2vsBase', 'expVMTvsBase',
                                                        'damSafetyvsBase', 'damNoisevsBase', 'damNonCO2vsBase', 'damCO2vsBase', 'damVMTvsBase',
                                                        'initSafetyvsBase', 'initNoisevsBase', 'initNonCO2vsBase', 'initCO2vsBase', 'initVMTvsBase',
                                                        'expSafetyvsBase_baseyr', 'expNoisevsBase_baseyr', 'expNonCO2vsBase_baseyr', 'expCO2vsBase_baseyr', 'expVMTvsBase_baseyr',
                                                        'damSafetyvsBase_baseyr', 'damNoisevsBase_baseyr', 'damNonCO2vsBase_baseyr', 'damCO2vsBase_baseyr', 'damVMTvsBase_baseyr',
                                                        'initSafetyvsBase_baseyr', 'initNoisevsBase_baseyr', 'initNonCO2vsBase_baseyr', 'initCO2vsBase_baseyr', 'initVMTvsBase_baseyr']] = 0

    logger.debug("interpolating base year and future year runs to calculate metrics across entire analysis period")
    final_table = pd.DataFrame()

    # NOTE: event probability is assumed to be specified for start_year not base_year
    logger.debug("Event Probability assumed to specify probability in start year of period of analysis, not base year")

    for index, row in df_base.iterrows():
        start_frac = (start_year - base_year) / (future_year - base_year)
        end_frac = (end_year - base_year) / (future_year - base_year)

        temp_stage = copy.deepcopy(row)

        initTrips = create_annual_stream(row, 'initTripslevels', start_year, end_year, start_frac, end_frac)
        temp_stage['initTripslevels'] = np.mean(initTrips)

        initVMT = create_annual_stream(row, 'initVMTlevels', start_year, end_year, start_frac, end_frac)
        temp_stage['initVMTlevels'] = np.mean(initVMT)

        initPHT = create_annual_stream(row, 'initPHTlevels', start_year, end_year, start_frac, end_frac)
        temp_stage['initPHTlevels'] = np.mean(initPHT)

        expTrips = create_annual_stream(row, 'expTripslevels', start_year, end_year, start_frac, end_frac)
        temp_stage['expTripslevels'] = np.mean(expTrips)

        expVMT = create_annual_stream(row, 'expVMTlevels', start_year, end_year, start_frac, end_frac)
        temp_stage['expVMTlevels'] = np.mean(expVMT)

        expPHT = create_annual_stream(row, 'expPHTlevels', start_year, end_year, start_frac, end_frac)
        temp_stage['expPHTlevels'] = np.mean(expPHT)

        damTrips = create_annual_stream(row, 'damTripslevels', start_year, end_year, start_frac, end_frac)
        temp_stage['damTripslevels'] = np.mean(damTrips)

        damVMT = create_annual_stream(row, 'damVMTlevels', start_year, end_year, start_frac, end_frac)
        temp_stage['damVMTlevels'] = np.mean(damVMT)

        damPHT = create_annual_stream(row, 'damPHTlevels', start_year, end_year, start_frac, end_frac)
        temp_stage['damPHTlevels'] = np.mean(damPHT)

        # NOTE: no annualization of init/exp/damTripslevel_dollar since not calculated
        initVMT_dollar = create_annual_stream(row, 'initVMTlevel_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['initVMTlevel_dollar'] = np.mean(initVMT_dollar)

        initPHT_dollar = create_annual_stream(row, 'initPHTlevel_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['initPHTlevel_dollar'] = np.mean(initPHT_dollar)

        expVMT_dollar = create_annual_stream(row, 'expVMTlevel_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['expVMTlevel_dollar'] = np.mean(expVMT_dollar)

        expPHT_dollar = create_annual_stream(row, 'expPHTlevel_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['expPHTlevel_dollar'] = np.mean(expPHT_dollar)

        damVMT_dollar = create_annual_stream(row, 'damVMTlevel_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['damVMTlevel_dollar'] = np.mean(damVMT_dollar)

        damPHT_dollar = create_annual_stream(row, 'damPHTlevel_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['damPHTlevel_dollar'] = np.mean(damPHT_dollar)

        initTripsvsBase = create_annual_stream(row, 'initTripsvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['initTripsvsBase'] = np.mean(initTripsvsBase)

        initVMTvsBase = create_annual_stream(row, 'initVMTvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['initVMTvsBase'] = np.mean(initVMTvsBase)

        initPHTvsBase = create_annual_stream(row, 'initPHTvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['initPHTvsBase'] = np.mean(initPHTvsBase)

        initTripsvsBase_dollar = create_annual_stream(row, 'initTripsvsBase_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['initTripsvsBase_dollar'] = np.mean(initTripsvsBase_dollar)

        initVMTvsBase_dollar = create_annual_stream(row, 'initVMTvsBase_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['initVMTvsBase_dollar'] = np.mean(initVMTvsBase_dollar)

        initPHTvsBase_dollar = create_annual_stream(row, 'initPHTvsBase_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['initPHTvsBase_dollar'] = np.mean(initPHTvsBase_dollar)

        expTripsvsBase = create_annual_stream(row, 'expTripsvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['expTripsvsBase'] = np.mean(expTripsvsBase)

        expVMTvsBase = create_annual_stream(row, 'expVMTvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['expVMTvsBase'] = np.mean(expVMTvsBase)

        expPHTvsBase = create_annual_stream(row, 'expPHTvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['expPHTvsBase'] = np.mean(expPHTvsBase)

        expTripsvsBase_dollar = create_annual_stream(row, 'expTripsvsBase_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['expTripsvsBase_dollar'] = np.mean(expTripsvsBase_dollar)

        expVMTvsBase_dollar = create_annual_stream(row, 'expVMTvsBase_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['expVMTvsBase_dollar'] = np.mean(expVMTvsBase_dollar)

        expPHTvsBase_dollar = create_annual_stream(row, 'expPHTvsBase_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['expPHTvsBase_dollar'] = np.mean(expPHTvsBase_dollar)

        damTripsvsBase = create_annual_stream(row, 'damTripsvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['damTripsvsBase'] = np.mean(damTripsvsBase)

        damVMTvsBase = create_annual_stream(row, 'damVMTvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['damVMTvsBase'] = np.mean(damVMTvsBase)

        damPHTvsBase = create_annual_stream(row, 'damPHTvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['damPHTvsBase'] = np.mean(damPHTvsBase)

        damTripsvsBase_dollar = create_annual_stream(row, 'damTripsvsBase_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['damTripsvsBase_dollar'] = np.mean(damTripsvsBase_dollar)

        damVMTvsBase_dollar = create_annual_stream(row, 'damVMTvsBase_dollar', start_year, end_year, start_frac, end_frac)
        temp_stage['damVMTvsBase_dollar'] = np.mean(damVMTvsBase_dollar)

        damPHTvsBase_dollar = create_annual_stream(row, 'damPHTvsBase_dollar', start_year, end_year, start_frac, end_frac)
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
        initSafetyvsBase = create_annual_stream(row, 'initSafetyvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['initSafetyvsBase'] = np.mean(initSafetyvsBase)
        temp_stage['initSafety_Discounted'] = np.sum(initSafetyvsBase / discount)

        expSafetyvsBase = create_annual_stream(row, 'expSafetyvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['expSafetyvsBase'] = np.mean(expSafetyvsBase)
        temp_stage['expSafety_Discounted'] = np.sum(expSafetyvsBase / discount)

        damSafetyvsBase = create_annual_stream(row, 'damSafetyvsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['damSafetyvsBase'] = np.mean(damSafetyvsBase)
        temp_stage['damSafety_Discounted'] = np.sum(damSafetyvsBase / discount)

        # noise calculations
        initNoisevsBase = create_annual_stream(row, 'initNoisevsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['initNoisevsBase'] = np.mean(initNoisevsBase)
        temp_stage['initNoise_Discounted'] = np.sum(initNoisevsBase / discount)

        expNoisevsBase = create_annual_stream(row, 'expNoisevsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['expNoisevsBase'] = np.mean(expNoisevsBase)
        temp_stage['expNoise_Discounted'] = np.sum(expNoisevsBase / discount)

        damNoisevsBase = create_annual_stream(row, 'damNoisevsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['damNoisevsBase'] = np.mean(damNoisevsBase)
        temp_stage['damNoise_Discounted'] = np.sum(damNoisevsBase / discount)

        # emissions calculations
        initNonCO2vsBase = create_annual_stream(row, 'initNonCO2vsBase', start_year, end_year, start_frac, end_frac)
        initCO2vsBase = create_annual_stream(row, 'initCO2vsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['initEmissionsvsBase'] = np.mean(initNonCO2vsBase + initCO2vsBase)
        temp_stage['initEmissions_Discounted'] = np.sum(initNonCO2vsBase / discount) + np.sum(initCO2vsBase / co2_discount)

        expNonCO2vsBase = create_annual_stream(row, 'expNonCO2vsBase', start_year, end_year, start_frac, end_frac)
        expCO2vsBase = create_annual_stream(row, 'expCO2vsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['expEmissionsvsBase'] = np.mean(expNonCO2vsBase + expCO2vsBase)
        temp_stage['expEmissions_Discounted'] = np.sum(expNonCO2vsBase / discount) + np.sum(expCO2vsBase / co2_discount)

        damNonCO2vsBase = create_annual_stream(row, 'damNonCO2vsBase', start_year, end_year, start_frac, end_frac)
        damCO2vsBase = create_annual_stream(row, 'damCO2vsBase', start_year, end_year, start_frac, end_frac)
        temp_stage['damEmissionsvsBase'] = np.mean(damNonCO2vsBase + damCO2vsBase)
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

        temp_stage['Benefits_Discounted'] = (np.sum((expTripsvsBase_dollar - expVMTvsBase_dollar - expPHTvsBase_dollar
                                                     - expSafetyvsBase - expNoisevsBase - expNonCO2vsBase
                                                     - row['AssetDamagevsBase_dollar'] + damTripsvsBase_dollar
                                                     - damVMTvsBase_dollar - damPHTvsBase_dollar - damSafetyvsBase
                                                     - damNoisevsBase - damNonCO2vsBase)
                                                    * event_prob / discount) +
                                             np.sum((0 - expCO2vsBase - damCO2vsBase)
                                                    * event_prob / co2_discount) +
                                             temp_stage['TotalResidual_Discounted'] -
                                             temp_stage['TotalMaintenanceCosts_Discounted'])
        temp_stage['ExpBenefits_Discounted'] = (np.sum((expTripsvsBase_dollar - expVMTvsBase_dollar
                                                        - expPHTvsBase_dollar - expSafetyvsBase - expNoisevsBase
                                                        - expNonCO2vsBase) * event_prob / discount) +
                                                np.sum((0 - expCO2vsBase) * event_prob / co2_discount))
        temp_stage['RepairCleanupCostSavings_Discounted'] = np.sum((0 - row['AssetDamagevsBase_dollar']) *
                                                                   event_prob / discount)
        temp_stage['DamBenefits_Discounted'] = (np.sum((damTripsvsBase_dollar - damVMTvsBase_dollar
                                                        - damPHTvsBase_dollar - damSafetyvsBase - damNoisevsBase
                                                        - damNonCO2vsBase) * event_prob / discount) +
                                                np.sum((0 - damCO2vsBase) * event_prob / co2_discount))
        temp_stage['NetBenefits_Discounted'] = temp_stage['Benefits_Discounted'] - temp_stage['ProjectCosts_Discounted']
        if temp_stage['ProjectCosts_Discounted'] == 0:
            temp_stage['BCR_Discounted'] = np.nan
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
    BCAnohazard = BCAnohazard.rename({'Benefits_Discounted': 'TotalNetBenefits_Discounted'}, axis='columns')
    final_table = pd.merge(final_table, BCAnohazard, how='left',
                           on=['Resiliency Project', 'Project Group', 'IDScenarioNoHazard'])
    final_table['TotalNetBenefits_Discounted'] = (final_table['TotalNetBenefits_Discounted'] -
                                                  final_table['ProjectCosts_Discounted'])

    # create column 'RegretAll' as ranking of 'TotalNetBenefits_Discounted'
    # for resiliency projects averaged across all uncertainty scenarios
    # average is to equally weight 'no' Resiliency Project baseline case across project groups
    # with other Resiliency Project cases
    # NOTE: use average across baseline scenarios as the baseline scenario counted in the Tableau summary dashboard
    logger.debug("calculating regret metrics")
    BCAmean = final_table.loc[:, ['Resiliency Project', 'TotalNetBenefits_Discounted']].groupby('Resiliency Project',
                                                                                           as_index=False,
                                                                                           sort=False).mean()
    BCAmean['RegretAll'] = BCAmean['TotalNetBenefits_Discounted'].rank(method='dense', ascending=False)
    final_table = pd.merge(final_table, BCAmean.loc[:, ['Resiliency Project', 'RegretAll']],
                           how='left', on='Resiliency Project')
    # create column 'RegretScenario' as ranking of 'TotalNetBenefits_Discounted'
    # for resiliency projects grouped by uncertainty scenario (across project groups)
    BCAbyScenario = final_table.loc[:, ['ID-Uncertainty Scenario', 'Resiliency Project',
                                        'TotalNetBenefits_Discounted']].groupby(['ID-Uncertainty Scenario',
                                                                                 'Resiliency Project'],
                                                                                as_index=False, sort=False).mean()
    BCAbyScenario['RegretScenario'] = BCAbyScenario.groupby('ID-Uncertainty Scenario')['TotalNetBenefits_Discounted'].rank(
        method='dense', ascending=False)
    final_table = pd.merge(final_table, BCAbyScenario.loc[:, ['ID-Uncertainty Scenario', 'Resiliency Project',
                                                              'RegretScenario']],
                           how='left', on=['ID-Uncertainty Scenario', 'Resiliency Project'])
    # create column 'RegretAsset' as ranking of 'TotalNetBenefits_Discounted'
    # for resiliency projects grouped by uncertainty scenario and asset
    BCAbyAsset = final_table.loc[:, ['ID-Uncertainty Scenario', 'Asset', 'Resiliency Project',
                                     'TotalNetBenefits_Discounted']].groupby(['ID-Uncertainty Scenario', 'Asset',
                                                                              'Resiliency Project'],
                                                                             as_index=False, sort=False).mean()
    BCAbyAsset['RegretAsset'] = BCAbyAsset.groupby(['ID-Uncertainty Scenario', 'Asset'])['TotalNetBenefits_Discounted'].rank(
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
                                           'initPHTlevels_baseyr_base', 'initVMTlevel_dollar_baseyr',
                                           'initSafetylevel_dollar_baseyr', 'initNoiselevel_dollar_baseyr',
                                           'initNonCO2level_dollar_baseyr', 'initCO2level_dollar_baseyr',
                                           'initPHTlevel_dollar_baseyr', 'expTripslevels_baseyr',
                                           'expVMTlevels_baseyr', 'expPHTlevels_baseyr',
                                           'expTripslevels_baseyr_base', 'expVMTlevels_baseyr_base',
                                           'expPHTlevels_baseyr_base', 'expVMTlevel_dollar_baseyr',
                                           'expSafetylevel_dollar_baseyr', 'expNoiselevel_dollar_baseyr',
                                           'expNonCO2level_dollar_baseyr', 'expCO2level_dollar_baseyr',
                                           'expPHTlevel_dollar_baseyr', 'damTripslevels_baseyr', 'damVMTlevels_baseyr',
                                           'damPHTlevels_baseyr', 'damVMTlevel_dollar_baseyr',
                                           'damSafetylevel_dollar_baseyr', 'damNoiselevel_dollar_baseyr',
                                           'damNonCO2level_dollar_baseyr', 'damCO2level_dollar_baseyr',
                                           'damPHTlevel_dollar_baseyr', 'initTripsvsBase_baseyr', 'initVMTvsBase_baseyr',
                                           'initPHTvsBase_baseyr', 'initTripsvsBase_dollar_baseyr',
                                           'initVMTvsBase_dollar_baseyr', 'initPHTvsBase_dollar_baseyr',
                                           'initSafetyvsBase_baseyr', 'initNoisevsBase_baseyr',
                                           'initNonCO2vsBase_baseyr', 'initCO2vsBase_baseyr',
                                           'expTripsvsBase_baseyr', 'expVMTvsBase_baseyr', 'expPHTvsBase_baseyr',
                                           'expTripsvsBase_dollar_baseyr', 'expVMTvsBase_dollar_baseyr',
                                           'expSafetyvsBase_baseyr', 'expNoisevsBase_baseyr',
                                           'expNonCO2vsBase_baseyr', 'expCO2vsBase_baseyr',
                                           'expPHTvsBase_dollar_baseyr', 'damTripsvsBase_baseyr', 'damVMTvsBase_baseyr',
                                           'damPHTvsBase_baseyr', 'damTripsvsBase_dollar_baseyr', 'damVMTvsBase_dollar_baseyr',
                                           'damSafetyvsBase_baseyr', 'damNoisevsBase_baseyr',
                                           'damNonCO2vsBase_baseyr', 'damCO2vsBase_baseyr',
                                           'damPHTvsBase_dollar_baseyr'],
                                   axis=1)

    # output in a form easily read by Tableau
    tableau_names = {'ID-Resiliency-Scenario': 'IDResiliencyScenario', 'ID-Uncertainty Scenario': 'IDScenario',
                     'Total Duration': 'DurationofEntireEventdays', 'Exposure Recovery Path': 'Exposurerecoverypath',
                     'Economic': 'EconomicScenario', 'Trip Loss Elasticity': 'TripElasticity',
                     'Future Event Frequency': 'FutureEventFrequency', 'Resiliency Project': 'ResiliencyProject',
                     'Project Name': 'ProjectName',
                     'repair_time': 'DamageDuration', 'AssetDamagelevel_dollar': 'RepairCleanupCosts',
                     'AssetDamagevsBase_dollar': 'RepairCleanupCostSavings', 'damage_repair': 'RepairCostSavings'}
    final_table = final_table.rename(tableau_names, axis='columns')

    bca_headers = ['EconomicScenario', 'TripElasticity', 'FutureEventFrequency', 'IDScenarioNoHazard', 'DurationofEntireEventdays',
                   'Exposurerecoverypath', 'IDScenario', 'ResiliencyProject', 'Project Group', 'IDResiliencyScenario', 'initTripslevels',
                   'initVMTlevels', 'initPHTlevels', 'expTripslevels', 'expVMTlevels', 'expPHTlevels',
                   'initVMTlevel_dollar', 'initPHTlevel_dollar', 'expVMTlevel_dollar', 'expPHTlevel_dollar',
                   'ProjectName', 'Asset', 'Estimated Project Cost', 'Project Lifespan', 'Estimated Maintenance Cost',
                   'Estimated Redeployment Cost', 'ResiliencyProjectAsset', 'HazardDim1', 'HazardDim2', 'Hazard Event', 'Event Probability',
                   'Year', 'damage_repair_base', 'total_repair_base', 'repair_time_base', 'damage_base', 'RepairCostSavings',
                   'DamageDuration', 'initTripslevels_max', 'initVMTlevels_max', 'initPHTlevels_max', 'initTripslevels_baseyr_max',
                   'initVMTlevels_baseyr_max', 'initPHTlevels_baseyr_max', 'DamageRecoveryPath', 'AssetDamagelevels', 'RepairCleanupCosts',
                   'damTripslevels', 'damVMTlevels', 'damPHTlevels', 'damVMTlevel_dollar', 'damPHTlevel_dollar',
                   'initTripsvsBase', 'initVMTvsBase', 'initPHTvsBase', 'expTripsvsBase', 'expVMTvsBase', 'expPHTvsBase', 'damTripsvsBase',
                   'damVMTvsBase', 'damPHTvsBase', 'initTripsvsBase_dollar', 'initVMTvsBase_dollar', 'initSafetyvsBase',
                   'initNoisevsBase', 'initNonCO2vsBase', 'initCO2vsBase', 'initPHTvsBase_dollar',
                   'expTripsvsBase_dollar', 'expVMTvsBase_dollar', 'expSafetyvsBase', 'expNoisevsBase',
                   'expNonCO2vsBase', 'expCO2vsBase', 'expPHTvsBase_dollar', 'damTripsvsBase_dollar', 'damVMTvsBase_dollar',
                   'damSafetyvsBase', 'damNoisevsBase', 'damNonCO2vsBase', 'damCO2vsBase',
                   'damPHTvsBase_dollar', 'AssetDamagevsBase', 'RepairCleanupCostSavings', 'initSafety_Discounted', 'expSafety_Discounted',
                   'damSafety_Discounted', 'initNoise_Discounted', 'expNoise_Discounted', 'damNoise_Discounted', 'initEmissions_Discounted',
                   'expEmissions_Discounted', 'damEmissions_Discounted', 'ProjectCosts_Discounted', 'TotalResidual_Discounted',
                   'TotalMaintenanceCosts_Discounted', 'Benefits_Discounted', 'ExpBenefits_Discounted', 'RepairCleanupCostSavings_Discounted',
                   'DamBenefits_Discounted', 'NetBenefits_Discounted', 'BCR_Discounted', 'TotalNetBenefits_Discounted', 'RegretAll',
                   'RegretScenario', 'RegretAsset']

    # print out output file with all baseline scenarios for records
    all_baselines_file = os.path.join(output_folder, 'bca_metrics_' + str(cfg['run_id']) + '.csv')
    logger.debug("Size of BCA table with all baseline scenarios: {}".format(final_table.shape))
    with open(all_baselines_file, "w", newline='') as f:
        final_table.to_csv(f, columns=bca_headers, index=False)
        logger.result("BCA table with all baseline scenarios written to {}".format(all_baselines_file))

    # if regret analysis, zero out BCA values
    if roi_analysis_type == 'Regret':
        final_table['Benefits_Discounted'] = 0
        final_table['NetBenefits_Discounted'] = 0
        final_table['TotalNetBenefits_Discounted'] = 0
    
    # assign 'IDResiliencyScenario' = 0, 'Project Group' = 'None' for all baseline averages
    tableau_table = final_table.drop(['Hazard Event', 'Project Group'], axis=1).groupby(['IDScenario',
                                                                        'ResiliencyProject',
                                                                        'ProjectName', 'Asset',
                                                                        'ResiliencyProjectAsset',
                                                                        'Year', 'EconomicScenario',
                                                                        'Exposurerecoverypath',
                                                                        'DamageRecoveryPath'],
                                                                       as_index=False, sort=False).mean()
    tableau_table = pd.merge(tableau_table, projgroup_to_resil, how='left',
                             left_on='ResiliencyProject', right_on='Resiliency Projects', indicator=True)
    logger.debug(("Number of resilience projects not matched to project " +
                  "groups: {}".format(sum(tableau_table.loc[tableau_table['ResiliencyProject'] != 'no', '_merge'] == 'left_only'))))
    if sum(tableau_table.loc[tableau_table['ResiliencyProject'] != 'no', '_merge'] == 'left_only') > 0:
        logger.warning(("TABLE JOIN WARNING: Some resilience projects in the Tableau input file were not " +
                        "found in ProjectGroups tab of Model_Parameters.xlsx and will not be matched to project groups."))
    tableau_table = tableau_table.drop(labels=['Resiliency Projects', '_merge'], axis=1)
    tableau_table = tableau_table.rename({'Project Groups': 'Project Group'}, axis='columns')
    tableau_table.loc[tableau_table['ResiliencyProject'] == 'no', ['IDResiliencyScenario']] = 0
    tableau_table.loc[tableau_table['ResiliencyProject'] == 'no', ['Project Group']] = 'None'

    # create a Parameters table for Tableau based on CSV file in config file with cfg values joined in
    parameters_table = check_file_exists(os.path.join(os.path.abspath(os.path.join(os.getcwd(), os.pardir)),
                                                      'config',
                                                      'parameters_lookup.csv'), logger)
    logger.config("Reading in parameters file: {}".format(parameters_table))
    parameters = pd.read_csv(parameters_table,
                             usecols=['Category', 'Parameter', 'Description'],
                             converters={'Category': str, 'Parameters': str, 'Description': str})
    parameters['Value'] = ""
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
    bca_table_agg = final_table.loc[:, ['ProjectName', 'IDScenarioNoHazard',
                                        'Hazard Event', 'Benefits_Discounted',
                                        'BCR_Discounted']].groupby(['ProjectName', 'IDScenarioNoHazard',
                                                                    'Hazard Event'],
                                                                    as_index=False, sort=False).mean()
    bca_table_agg = bca_table_agg.drop(['IDScenarioNoHazard'], axis=1).groupby(['ProjectName', 'Hazard Event'],
                                                                         as_index=False, sort=False).mean()

    bca_table_1 = bca_table_agg.loc[:, ['ProjectName', 'Hazard Event', 'Benefits_Discounted']]
    bca_table_1 = pd.melt(bca_table_1, id_vars=['ProjectName', 'Hazard Event'], value_vars=['Benefits_Discounted'])
    bca_table_1 = bca_table_1.rename({'Hazard Event': 'Hazard', 'variable': 'Attribute', 'value': 'Value'}, axis='columns')

    bca_table_2 = tableau_table.loc[:, ['ProjectName', 'ProjectCosts_Discounted',
                                        'TotalNetBenefits_Discounted']].groupby(['ProjectName'],
                                                                                as_index=False,
                                                                                sort=False).mean()
    bca_table_2['ProjectCosts_Discounted'] = 0 - bca_table_2['ProjectCosts_Discounted']
    bca_table_2 = pd.melt(bca_table_2, id_vars=['ProjectName'], value_vars=['ProjectCosts_Discounted',
                                                                            'TotalNetBenefits_Discounted'])
    bca_table_2 = bca_table_2.rename({'variable': 'Attribute', 'value': 'Value'}, axis='columns')
    bca_table_2['Hazard'] = ''

    bca_table_3 = bca_table_agg.drop(['Hazard Event'], axis=1).groupby('ProjectName', as_index=False,
                                                                       sort=False).sum()
    bca_table_3 = pd.melt(bca_table_3, id_vars=['ProjectName'], value_vars=['Benefits_Discounted',
                                                                            'BCR_Discounted'])
    bca_table_3 = bca_table_3.rename({'variable': 'Attribute', 'value': 'Value'}, axis='columns')
    bca_table_3['Hazard'] = ''

    bca_table = pd.concat([bca_table_1, bca_table_2, bca_table_3], ignore_index=True)

    # if regret analysis, zero out BCA values
    if roi_analysis_type == 'Regret':
        bca_table['Value'] = 0

    # create visualization table iff TrueShape.csv exists
    true_shape_file = os.path.join(input_folder, 'LookupTables', 'TrueShape.csv')

    if os.path.exists(true_shape_file):
        geom_table = geom_process(true_shape_file, cfg['crs'], logger)

        # group tableau_table by ResiliencyProject
        tableau_table_agg = tableau_table.loc[:, ['ResiliencyProject', 'RegretAll', 'RepairCleanupCostSavings_Discounted',
                                                  'TotalNetBenefits_Discounted', 'ProjectCosts_Discounted']].groupby(['ResiliencyProject'],
                                                                                                                     as_index=False, sort=False).mean()
        # left join based on geom_table
        # use columns Overall Regret, Average Project Repair Savings, Average Project Net Benefits, Overall Project Costs
        visualization_table = pd.merge(left = geom_table, right = tableau_table_agg, how = 'left',
                                       left_on = ['Project ID'], right_on = ['ResiliencyProject'])
        visualization_table.rename({'RegretAll': 'Overall Regret', 'RepairCleanupCostSavings_Discounted': 'Average Project Repair Savings',
                                    'TotalNetBenefits_Discounted': 'Average Project Net Benefits',
                                    'ProjectCosts_Discounted': 'Overall Project Costs'}, axis='columns', inplace=True)
        visualization_table.drop(labels=['ResiliencyProject'], axis=1, inplace=True)

        # add baseline_exposure average from hazard tables
        exposures_folder = os.path.join(input_folder, 'Hazards')
        depths = pd.DataFrame()
        for index, row in hazard_levels.iterrows():
            filename = str(row['Filename']) + '.csv'
            temp_depths = pd.read_csv(os.path.join(exposures_folder, filename),
                                      usecols=['link_id', cfg['exposure_field']],
                                      converters={'link_id': str, cfg['exposure_field']: float})
            temp_depths.drop_duplicates(subset=['link_id'], inplace=True, ignore_index=True)
            # catch any empty values in exposure field and set to 0 exposure
            temp_depths[cfg['exposure_field']] = temp_depths[cfg['exposure_field']].fillna(0)
            depths = pd.concat([depths, temp_depths], ignore_index=True)
        # group depths by link_id and average cfg['exposure_field']
        depths_agg = depths.loc[:, ['link_id', cfg['exposure_field']]].groupby(['link_id'], as_index=False, sort=False).mean()
        depths_agg.rename({cfg['exposure_field']: 'Average Link Exposure'}, axis='columns', inplace=True)
        # use columns Average Link Exposure, merge
        visualization_table = pd.merge(left = visualization_table, right = depths_agg, how = 'left',
                                       on = 'link_id')

        visualization_table = gpd.GeoDataFrame(
            visualization_table, crs = cfg['crs'], geometry = 'geometry')
        visualization_table = visualization_table.to_crs('EPSG:4326')
    else:
        visualization_table = pd.DataFrame(columns = ['link_id', 'WKT', 'Project ID', 'Category', 'Exposure Reduction',
                                                      'Overall Regret', 'Average Project Repair Savings',
                                                      'Average Project Net Benefits', 'Overall Project Costs',
                                                      'Average Link Exposure', 'geometry'])

    tableau_file = os.path.join(output_folder, 'tableau_input_file_' + str(cfg['run_id']) + '.xlsx')
    logger.result("Tableau dashboard input table written to {}".format(tableau_file))
    with pd.ExcelWriter(tableau_file) as writer:
        # write scenario output metrics
        tableau_table.to_excel(writer, sheet_name="Scenarios", index=False,
                               columns=['Year', 'IDResiliencyScenario', 'IDScenario', 'IDScenarioNoHazard',
                                        'EconomicScenario', 'TripElasticity', 'FutureEventFrequency', 'HazardDim1',
                                        'HazardDim2', 'Event Probability', 'DurationofEntireEventdays',
                                        'Exposurerecoverypath', 'DamageRecoveryPath', 'Project Group', 'ResiliencyProject',
                                        'ProjectName', 'Asset', 'ResiliencyProjectAsset', 'ProjectCosts_Discounted',
                                        'TotalNetBenefits_Discounted', 'NetBenefits_Discounted', 'Benefits_Discounted',
                                        'ExpBenefits_Discounted', 'RepairCleanupCostSavings_Discounted',
                                        'DamBenefits_Discounted', 'BCR_Discounted', 'RegretAll', 'RegretScenario',
                                        'RegretAsset', 'initTripslevels', 'initTripsvsBase',
                                        'initTripsvsBase_dollar', 'initVMTlevels', 'initVMTlevel_dollar', 'initVMTvsBase',
                                        'initVMTvsBase_dollar', 'initSafetyvsBase', 'initNoisevsBase', 'initNonCO2vsBase',
                                        'initCO2vsBase', 'initPHTlevels', 'initPHTlevel_dollar', 'initPHTvsBase',
                                        'initPHTvsBase_dollar', 'expTripslevels', 'expTripsvsBase',
                                        'expTripsvsBase_dollar', 'expVMTlevels', 'expVMTlevel_dollar', 'expVMTvsBase',
                                        'expVMTvsBase_dollar', 'expSafetyvsBase', 'expNoisevsBase', 'expNonCO2vsBase',
                                        'expCO2vsBase', 'expPHTlevels', 'expPHTlevel_dollar', 'expPHTvsBase',
                                        'expPHTvsBase_dollar', 'damTripslevels', 'damTripsvsBase',
                                        'damTripsvsBase_dollar', 'damVMTlevels', 'damVMTlevel_dollar', 'damVMTvsBase',
                                        'damVMTvsBase_dollar', 'damSafetyvsBase', 'damNoisevsBase', 'damNonCO2vsBase',
                                        'damCO2vsBase', 'damPHTlevels', 'damPHTlevel_dollar', 'damPHTvsBase',
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
        # write visualization table (empty if TrueShape.csv wasn't provided)
        visualization_table.to_excel(writer, sheet_name="Visualization", index=False)

    tableau_dir = prepare_tableau_assets(tableau_file, output_folder, cfg, logger)
    logger.result("Tableau dashboard written to directory {}".format(tableau_dir))

    logger.info("Finished: recovery analysis module")


# ==============================================================================


# helper function to create an annualized stream of metric stored as var_name
def create_annual_stream(row, var_name, start_year, end_year, start_frac, end_frac):
    var_startyr = (row[var_name + '_baseyr'] + 
                   start_frac * (row[var_name] - row[var_name + '_baseyr']))
    var_endyr = (row[var_name + '_baseyr'] +
                 end_frac * (row[var_name] - row[var_name + '_baseyr']))
    return np.linspace(var_startyr, var_endyr, end_year - start_year + 1)


# ==============================================================================


# check ROI inputs based on ROI Analysis Type parameter
def check_roi_required_inputs(input_folder, cfg, logger):
    logger.info("Start: check_roi_required_inputs")
    is_covered = 1

    if cfg['cfg_type'] == 'config':
        model_params_file = check_file_exists(os.path.join(input_folder, 'Model_Parameters.xlsx'), logger)
        model_params = pd.read_excel(model_params_file, sheet_name='Hazards',
                                     usecols=['Hazard Event', 'Event Probability in Start Year'],
                                     converters={'Hazard Event': str, 'Event Probability in Start Year': float})
    else:  # cfg_type = 'json'
        model_params = cfg['hazards']

    # check 'Event Probability in Start Year' for non-negative values
    if (model_params['Event Probability in Start Year'] < 0).any():
        logger.error("Note: Hazard event probability must be a non-negative number.")

    project_table = check_file_exists(os.path.join(input_folder, 'LookupTables', 'project_info.csv'), logger)
    projects = pd.read_csv(project_table, usecols=['Project ID', 'Project Cost', 'Project Lifespan'],
                           converters={'Project ID': str, 'Project Cost': str, 'Project Lifespan': int})
    # convert 'Project Cost' column to float type
    projects['Estimated Project Cost'] = projects['Project Cost'].replace('[\$,]', '', regex=True).replace('', '0.0').astype(float)

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
        # If project cost is nonzero, give a warning
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
    root_graphic4_location = os.path.join(config_directory, 'tableau_images', 'Picture2.png')
    if not os.path.exists(root_graphic4_location):
        logger.error("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_graphic4_location))
        raise Exception("TABLEAU REPORT INPUT FILE ERROR: {} could not be found".format(root_graphic4_location))
    shutil.copy(root_twb_location, os.path.join(tableau_directory, 'tableau_dashboard.twb'))
    shutil.copy(root_graphic1_location, tableau_directory)
    shutil.copy(root_graphic2_location, tableau_directory)
    shutil.copy(root_graphic3_location, tableau_directory)
    shutil.copy(root_graphic4_location, tableau_directory)

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
    zipObj.write(os.path.join(tableau_directory, 'Picture2.png'), 'Picture2.png')

    # close the Zip File
    zipObj.close()

    # delete the original files for clean up
    os.remove(os.path.join(tableau_directory, 'tableau_dashboard.twb'))
    os.remove(os.path.join(tableau_directory, 'tableau_input_file.xlsx'))
    os.remove(os.path.join(tableau_directory, 'dictionary_noBackground.png'))
    os.remove(os.path.join(tableau_directory, 'images.png'))
    os.remove(os.path.join(tableau_directory, 'Picture4.png'))
    os.remove(os.path.join(tableau_directory, 'Picture2.png'))

    # open tableau dashboard for Windows
    os.startfile(twbx_dashboard_filename)

    logger.info("Finished: prepare_tableau_assets")

    return tableau_directory


# ==============================================================================


def geom_process(true_shape_file: str, crs: str, logger) -> gpd.GeoDataFrame:
    """geom_process will take the TrueShape.csv and create a geopandas
    geodataframe."""

    true_shape_table = pd.read_csv(true_shape_file, usecols=['link_id', 'WKT'],
                                   converters={'link_id': str, 'WKT': str})
    true_shape_table = true_shape_table.drop_duplicates(ignore_index=True)

    # add asset column to TrueShape data, pulled in from project info and project table
    project_table_path = os.path.join(os.path.dirname(true_shape_file), 'project_table.csv')

    asset_link_id = pd.read_csv(project_table_path, converters={'link_id': str, 'Project ID': str, 'Category': str,
                                                                'Exposure Reduction': float})

    true_shape_table = pd.merge(left = true_shape_table, right = asset_link_id, on = 'link_id', how = 'left')
    logger.debug("Size of look-up table for wkt: {}".format(true_shape_table.shape))
    
    gdf = gpd.GeoDataFrame(true_shape_table, crs = crs, geometry = gpd.GeoSeries.from_wkt(true_shape_table['WKT']))

    if any(gdf.geom_type != 'LineString'):
        gdf = gdf.explode()

    return gdf

