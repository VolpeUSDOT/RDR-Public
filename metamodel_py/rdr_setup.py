#!/usr/bin/env python
# coding: utf-8


import sys
import os
import configparser
import json
import re
import pandas as pd
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'helper_tools', 'rdr_ui'))
# Import entire params.py file and use params.short_dict
import params

# ==============================================================================


def read_config_file_helper(config, cfg_type, section, key, required_or_optional, error_list):
    if cfg_type == 'config':
        if not config.has_option(section, key):
            if required_or_optional.upper() == 'REQUIRED':
                error_list.append("CONFIG FILE ERROR: Can't find {} in section {}".format(key, section))
                return error_list, None

            return error_list, None

        else:
            val = config.get(section, key).strip().strip("'").strip('"')

    else:  # cfg_type == 'json'
        # Find short name of parameter
        if key not in params.short_dict:
            error_list.append("CONFIG FILE ERROR: Can't find {} in UI parameters short_dict".format(key))
            return error_list, None
        short_key = params.short_dict[key]

        if short_key not in config or config[short_key] is None:
            if required_or_optional.upper() == 'REQUIRED':
                error_list.append("CONFIG FILE ERROR: Can't find {} in UI-prepared config file".format(key))
                return error_list, None

            return error_list, None

        else:
            val = str(config[short_key]).strip().strip("'").strip('"')

    if val == '':
        return error_list, None
    else:
        return error_list, val


# ==============================================================================


def read_config_file(cfg_file, cfg_type='config'):
    error_list = []  # list of errors to be written out to Run_RDR.py

    cfg_dict = {}  # return value

    if not os.path.exists(cfg_file):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_file))

    # Note in a parameter of cfg_dict what type of config file was used
    if cfg_type == 'config':
        cfg = configparser.RawConfigParser()
        cfg.read(cfg_file)
        cfg_dict['cfg_type'] = 'config'
    elif cfg_type == 'json':
        with open(cfg_file) as f:
            cfg = json.load(f)
        cfg_dict['cfg_type'] = 'json'
    else:
        raise Exception("CONFIG FILE TYPE ERROR: {} must have file extension config or json".format(cfg_file))

    # ===================
    # COMMON VALUES
    # ===================

    error_list, cfg_dict['input_dir'] = read_config_file_helper(cfg, cfg_type, 'common', 'input_dir', 'REQUIRED', error_list)

    automated_tests_directory = False
    if re.search('^\\.\\\\tests', cfg_dict['input_dir']):
        automated_tests_directory = True
        cfg_dict['input_dir'] = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), cfg_dict['input_dir']))

    if not os.path.exists(cfg_dict['input_dir']):
        error_list.append("CONFIG FILE ERROR: input directory {} can't be found".format(cfg_dict['input_dir']))

    error_list, cfg_dict['output_dir'] = read_config_file_helper(cfg, cfg_type, 'common', 'output_dir', 'REQUIRED', error_list)

    if re.search('^\\.\\\\tests', cfg_dict['output_dir']):
        automated_tests_directory = True
        cfg_dict['output_dir'] = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), cfg_dict['output_dir']))

    compare_run_id = False
    if not os.path.exists(cfg_dict['output_dir']):
        p = Path(cfg_dict['output_dir'])
        p.mkdir(parents=True, exist_ok=True)
        print('Created ' + cfg_dict['output_dir'])
    else:
        if not automated_tests_directory:
            if len(os.listdir(cfg_dict['output_dir'])) > 0:
                if os.path.exists(os.path.join(cfg_dict['output_dir'], 'logs')):
                    compare_run_id = True

    error_list, cfg_dict['run_id'] = read_config_file_helper(cfg, cfg_type, 'common', 'run_id', 'REQUIRED', error_list)
    if compare_run_id:
        if len(os.listdir(os.path.join(cfg_dict['output_dir'], 'logs'))) > 0:
            file_from_previous_run = os.listdir(os.path.join(cfg_dict['output_dir'], 'logs'))[0]
            previous_run_id = file_from_previous_run[file_from_previous_run.find('_log_')+5:-24]
            if not (previous_run_id == cfg_dict['run_id']):
                error_list.append("CONFIG FILE ERROR: new run ID {} differs from previous run ID {} found in current output directory {}. Specify new output directory for the new run ID.".format(
                                  cfg_dict['run_id'], previous_run_id, cfg_dict['output_dir']))

    error_list, value = read_config_file_helper(cfg, cfg_type, 'common', 'start_year', 'REQUIRED', error_list)
    cfg_dict['start_year'] = int(value)
    error_list, value = read_config_file_helper(cfg, cfg_type, 'common', 'end_year', 'REQUIRED', error_list)
    cfg_dict['end_year'] = int(value)
    error_list, value = read_config_file_helper(cfg, cfg_type, 'common', 'base_year', 'REQUIRED', error_list)
    cfg_dict['base_year'] = int(value)
    error_list, value = read_config_file_helper(cfg, cfg_type, 'common', 'future_year', 'REQUIRED', error_list)
    cfg_dict['future_year'] = int(value)

    if cfg_dict['end_year'] - cfg_dict['start_year'] < 0:
        error_list.append('Start year must be equal to or before the end year.')
    if cfg_dict['future_year'] - cfg_dict['base_year'] < 0:
        error_list.append('Base year must be equal to or before the future year.')

    # ===================
    # METAMODEL VALUES
    # ===================

    error_list, metamodel_type = read_config_file_helper(cfg, cfg_type, 'metamodel', 'metamodel_type', 'OPTIONAL', error_list)
    # Set default to 'multitarget' if this is not specified
    cfg_dict['metamodel_type'] = 'multitarget'
    if metamodel_type is not None:
        if metamodel_type not in ['base', 'interact', 'projgroupLM', 'multitarget', 'mixedeffects']:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for metamodel_type, see config file for possible options (case sensitive)".format(
                    metamodel_type))
        else:
            cfg_dict['metamodel_type'] = metamodel_type

    error_list, value = read_config_file_helper(cfg, cfg_type, 'metamodel', 'lhs_sample_target', 'REQUIRED', error_list)
    cfg_dict['lhs_sample_target'] = int(value)

    error_list, aeq_run_type = read_config_file_helper(cfg, cfg_type, 'metamodel', 'aeq_run_type', 'OPTIONAL', error_list)
    # Set default to routing if this is not specified
    cfg_dict['aeq_run_type'] = 'RT'
    if aeq_run_type is not None:
        aeq_run_type = aeq_run_type.upper()
        if aeq_run_type not in ['SP', 'RT']:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for aeq_run_type, should be 'SP' or 'RT'".format(
                    aeq_run_type))
        else:
            cfg_dict['aeq_run_type'] = aeq_run_type

    error_list, run_minieq = read_config_file_helper(cfg, cfg_type, 'metamodel', 'run_minieq', 'OPTIONAL', error_list)
    # Set default to 0 if this is not specified
    cfg_dict['run_minieq'] = 0
    if run_minieq is not None:
        run_minieq = int(run_minieq)
        if run_minieq not in [0, 1]:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for run_minieq, should be 1 or 0".format(str(run_minieq)))
        else:
            cfg_dict['run_minieq'] = run_minieq

    error_list, allow_centroid_flows = read_config_file_helper(cfg, cfg_type, 'metamodel', 'allow_centroid_flows', 'OPTIONAL', error_list)
    # Note that parameter used by AequilibraE is blocked_centroid_flows as T/F so translate config parameter accordingly
    # Set default to False if this is not specified
    cfg_dict['blocked_centroid_flows'] = False
    if allow_centroid_flows is not None:
        allow_centroid_flows = int(allow_centroid_flows)
        if allow_centroid_flows not in [0, 1]:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for allow_centroid_flows, should be 1 or 0".format(str(allow_centroid_flows)))
        else:
            if allow_centroid_flows == 0:
                cfg_dict['blocked_centroid_flows'] = True

    error_list, calc_transit_metrics = read_config_file_helper(cfg, cfg_type, 'metamodel', 'calc_transit_metrics', 'OPTIONAL', error_list)
    # Translate config parameter into T/F
    # Set default to True if this is not specified
    cfg_dict['calc_transit_metrics'] = True
    if calc_transit_metrics is not None:
        calc_transit_metrics = int(calc_transit_metrics)
        if calc_transit_metrics not in [0, 1]:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for calc_transit_metrics, should be 1 or 0".format(str(calc_transit_metrics)))
        else:
            if calc_transit_metrics == 0:
                cfg_dict['calc_transit_metrics'] = False

    if cfg_dict['calc_transit_metrics'] and cfg_dict['aeq_run_type'] == 'SP':
        error_list.append("CONFIG FILE ERROR: aeq_run_type must be set to 'RT' if calc_transit_metrics is set to 1")

    error_list, aeq_max_iter = read_config_file_helper(cfg, cfg_type, 'metamodel', 'aeq_max_iter', 'OPTIONAL', error_list)
    # Set default to 100 if this is not specified
    cfg_dict['aeq_max_iter'] = 100
    if aeq_max_iter is not None:
        aeq_max_iter = int(aeq_max_iter)
        if aeq_max_iter <= 0:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for aeq_max_iter, should be an integer greater than zero".format(str(aeq_max_iter)))
        else:
            cfg_dict['aeq_max_iter'] = aeq_max_iter

    error_list, aeq_rgap_target = read_config_file_helper(cfg, cfg_type, 'metamodel', 'aeq_rgap_target', 'OPTIONAL', error_list)
    # Set default to 0.01 if this is not specified
    cfg_dict['aeq_rgap_target'] = 0.01
    if aeq_rgap_target is not None:
        aeq_rgap_target = float(aeq_rgap_target)
        if aeq_rgap_target <= 0:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for aeq_rgap_target, should be a number greater than zero".format(str(aeq_rgap_target)))
        else:
            cfg_dict['aeq_rgap_target'] = aeq_rgap_target

    # ===================
    # DISRUPTION VALUES
    # ===================

    error_list, link_availability_approach = read_config_file_helper(cfg, cfg_type, 'disruption', 'link_availability_approach', 'OPTIONAL', error_list)
    # Set default to binary if this is not specified
    cfg_dict['link_availability_approach'] = 'binary'
    if link_availability_approach is not None:
        link_availability_approach = link_availability_approach.lower()
        if link_availability_approach not in ['binary', 'default_flood_exposure_function', 'manual', 'facility_type_manual',
                                              'beta_distribution_function']:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for link_availability_approach, ".format(link_availability_approach) +
                "should be 'binary', 'default_flood_exposure_function', 'manual', 'facility_type_manual', or " +
                "'beta_distribution_function'")
        else:
            cfg_dict['link_availability_approach'] = link_availability_approach

    error_list, cfg_dict['exposure_field'] = read_config_file_helper(cfg, cfg_type, 'disruption', 'exposure_field', 'REQUIRED', error_list)

    # See Recovery section below for definition of exposure unit parameter used by both disruption and recovery modules

    if cfg_dict['link_availability_approach'] == 'manual' or cfg_dict['link_availability_approach'] == 'facility_type_manual':
        error_list, cfg_dict['link_availability_csv'] = read_config_file_helper(cfg, cfg_type, 'disruption', 'link_availability_csv', 'REQUIRED', error_list)
    else:
        cfg_dict['link_availability_csv'] = None

    if cfg_dict['link_availability_approach'] == 'beta_distribution_function':
        error_list, value = read_config_file_helper(cfg, cfg_type, 'disruption', 'alpha', 'REQUIRED', error_list)
        cfg_dict['alpha'] = float(value)
        if cfg_dict['alpha'] <= 0:
            error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['alpha'])) +
                            "alpha, should be number greater than 0")
        error_list, value = read_config_file_helper(cfg, cfg_type, 'disruption', 'beta', 'REQUIRED', error_list)
        cfg_dict['beta'] = float(value)
        if cfg_dict['beta'] <= 0:
            error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['beta'])) +
                            "beta, should be number greater than 0")
        error_list, value = read_config_file_helper(cfg, cfg_type, 'disruption', 'lower_bound', 'REQUIRED', error_list)
        cfg_dict['lower_bound'] = float(value)
        error_list, value = read_config_file_helper(cfg, cfg_type, 'disruption', 'upper_bound', 'REQUIRED', error_list)
        cfg_dict['upper_bound'] = float(value)
        error_list, cfg_dict['beta_method'] = read_config_file_helper(cfg, cfg_type, 'disruption', 'beta_method', 'REQUIRED', error_list)
        if cfg_dict['beta_method'] not in ['lower cumulative', 'upper cumulative']:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for beta_method, ".format(cfg_dict['beta_method']) +
                "should be 'lower cumulative' or 'upper cumulative' (case sensitive)")
    else:
        cfg_dict['alpha'] = None
        cfg_dict['beta'] = None
        cfg_dict['lower_bound'] = None
        cfg_dict['upper_bound'] = None
        cfg_dict['beta_method'] = None

    error_list, zone_conn = read_config_file_helper(cfg, cfg_type, 'disruption', 'highest_zone_number', 'OPTIONAL', error_list)
    # Set default to 0 if this is not specified
    cfg_dict['zone_conn'] = 0
    if zone_conn is not None:
        zone_conn = int(zone_conn)
        if zone_conn < 0:
            error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(str(zone_conn)) +
                            "highest_zone_number, should be integer greater than or equal to 0")
        else:
            cfg_dict['zone_conn'] = zone_conn

    error_list, resil_mitigation_approach = read_config_file_helper(cfg, cfg_type, 'disruption', 'resil_mitigation_approach', 'OPTIONAL', error_list)
    # Set default to binary if this is not specified
    cfg_dict['resil_mitigation_approach'] = 'binary'
    if resil_mitigation_approach is not None:
        resil_mitigation_approach = resil_mitigation_approach.lower()
        if resil_mitigation_approach not in ['binary', 'manual']:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for ".format(resil_mitigation_approach) +
                "resil_mitigation_approach, should be 'binary' or 'manual'")
        else:
            cfg_dict['resil_mitigation_approach'] = resil_mitigation_approach

    # ===================
    # RECOVERY VALUES
    # ===================

    error_list, value = read_config_file_helper(cfg, cfg_type, 'recovery', 'min_duration', 'REQUIRED', error_list)
    cfg_dict['min_duration'] = float(value)
    error_list, value = read_config_file_helper(cfg, cfg_type, 'recovery', 'max_duration', 'REQUIRED', error_list)
    cfg_dict['max_duration'] = float(value)
    error_list, value = read_config_file_helper(cfg, cfg_type, 'recovery', 'num_duration_cases', 'REQUIRED', error_list)
    cfg_dict['num_duration_cases'] = int(value)

    error_list, cfg_dict['hazard_recov_type'] = read_config_file_helper(cfg, cfg_type, 'recovery', 'hazard_recov_type', 'REQUIRED', error_list)
    if cfg_dict['hazard_recov_type'] not in ['days', 'percent']:
        error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['hazard_recov_type']) +
                        "hazard_recov_type, should be 'days' or 'percent' (case sensitive)")

    error_list, hazard_recov_length = read_config_file_helper(cfg, cfg_type, 'recovery', 'hazard_recov_length', 'REQUIRED', error_list)
    if cfg_dict['hazard_recov_type'] == 'days':
        cfg_dict['hazard_recov_length'] = float(hazard_recov_length)

    if cfg_dict['hazard_recov_type'] == 'percent':
        cfg_dict['hazard_recov_length'] = float(hazard_recov_length.strip('%'))/100

    error_list, value = read_config_file_helper(cfg, cfg_type, 'recovery', 'hazard_recov_path_model',
                                                'REQUIRED', error_list)
    cfg_dict['hazard_recov_path_model'] = value.lower()
    if cfg_dict['hazard_recov_path_model'] not in ['equal']:
        error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['hazard_recov_path_model']) +
                        "hazard_recov_path_model, should be 'Equal'")

    error_list, exposure_damage_approach = read_config_file_helper(cfg, cfg_type, 'recovery', 'exposure_damage_approach', 'OPTIONAL', error_list)
    # Set default to binary if this is not specified
    cfg_dict['exposure_damage_approach'] = 'binary'
    if exposure_damage_approach is not None:
        exposure_damage_approach = exposure_damage_approach.lower()
        if exposure_damage_approach not in ['binary', 'default_damage_table', 'manual']:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for ".format(exposure_damage_approach) +
                "exposure_damage_approach, should be 'binary', 'default_damage_table', or 'manual'")
        else:
            cfg_dict['exposure_damage_approach'] = exposure_damage_approach

    # Set units of exposure if default flood exposure function or default depth-damage table is chosen
    # NOTE: need both cfg_dict['link_availability_approach'] and cfg_dict['exposure_damage_approach'] to be defined already
    if cfg_dict['link_availability_approach'] == 'default_flood_exposure_function' or cfg_dict['exposure_damage_approach'] == 'default_damage_table':
        error_list, cfg_dict['exposure_unit'] = read_config_file_helper(cfg, cfg_type, 'disruption', 'exposure_unit', 'REQUIRED', error_list)
        if cfg_dict['exposure_unit'].lower() not in ['feet', 'foot', 'ft', 'yards', 'yard', 'm', 'meters']:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for exposure_unit, ".format(cfg_dict['exposure_unit']) +
                "the default flood exposure function and default damage table are currently only compatible with " +
                "depths provided in 'feet', 'yards', or 'meters'")
    else:
        cfg_dict['exposure_unit'] = None

    if cfg_dict['exposure_damage_approach'] == 'manual':
        error_list, cfg_dict['exposure_damage_csv'] = read_config_file_helper(cfg, cfg_type, 'recovery', 'exposure_damage_csv', 'REQUIRED', error_list)
    else:
        cfg_dict['exposure_damage_csv'] = None

    error_list, value = read_config_file_helper(cfg, cfg_type, 'recovery', 'repair_cost_approach',
                                                'REQUIRED', error_list)
    cfg_dict['repair_cost_approach'] = value.lower()
    if cfg_dict['repair_cost_approach'] not in ['default', 'user-defined']:
        error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['repair_cost_approach']) +
                        "repair_cost_approach, should be 'default' or 'user-defined'")

    # Set network type if default repair cost table is chosen
    if cfg_dict['repair_cost_approach'] == 'default':
        error_list, cfg_dict['repair_network_type'] = read_config_file_helper(cfg, cfg_type, 'recovery', 'repair_network_type', 'REQUIRED', error_list)
        if cfg_dict['repair_network_type'] not in ['Rural Flat', 'Rural Rolling', 'Rural Mountainous', 'Small Urban',
                                                   'Small Urbanized', 'Large Urbanized', 'Major Urbanized']:
            error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['repair_network_type']) +
                            "repair_network_type, see config file for possible options (case sensitive)")
    else:
        cfg_dict['repair_network_type'] = None

    if cfg_dict['repair_cost_approach'] == 'user-defined':
        error_list, cfg_dict['repair_cost_csv'] = read_config_file_helper(cfg, cfg_type, 'recovery', 'repair_cost_csv', 'REQUIRED', error_list)
    else:
        cfg_dict['repair_cost_csv'] = None

    error_list, value = read_config_file_helper(cfg, cfg_type, 'recovery', 'repair_time_approach',
                                                'REQUIRED', error_list)
    cfg_dict['repair_time_approach'] = value.lower()
    if cfg_dict['repair_time_approach'] not in ['default', 'user-defined']:
        error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['repair_time_approach']) +
                        "repair_time_approach, should be 'default' or 'user-defined'")

    if cfg_dict['repair_time_approach'] == 'user-defined':
        error_list, cfg_dict['repair_time_csv'] = read_config_file_helper(cfg, cfg_type, 'recovery', 'repair_time_csv', 'REQUIRED', error_list)
    else:
        cfg_dict['repair_time_csv'] = None

    # ===================
    # ANALYSIS VALUES
    # ===================

    error_list, roi_analysis_type = read_config_file_helper(cfg, cfg_type, 'analysis', 'roi_analysis_type', 'REQUIRED', error_list)
    if roi_analysis_type not in ['BCA', 'Regret', 'Breakeven']:
        error_list.append(
            "CONFIG FILE ERROR: {} is an invalid value for roi_analysis_type, see config file for possible options (case sensitive)".format(
                roi_analysis_type))
    else:
        cfg_dict['roi_analysis_type'] = roi_analysis_type

    error_list, value = read_config_file_helper(cfg, cfg_type, 'analysis', 'dollar_year', 'REQUIRED', error_list)
    cfg_dict['dollar_year'] = int(value)

    error_list, discount_factor = read_config_file_helper(cfg, cfg_type, 'analysis', 'discount_factor', 'REQUIRED', error_list)
    if discount_factor is not None:
        discount_factor = float(discount_factor)
        if discount_factor <= -1:
            error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(str(discount_factor)) +
                              "discount_factor, should be decimal greater than -1")
        else:
            cfg_dict['discount_factor'] = discount_factor
    else:
        error_list.append("CONFIG FILE ERROR: discount_factor is a required parameter in the config file")

    error_list, co2_discount_factor = read_config_file_helper(cfg, cfg_type, 'analysis', 'co2_discount_factor', 'REQUIRED', error_list)
    if co2_discount_factor is not None:
        co2_discount_factor = float(co2_discount_factor)
        if co2_discount_factor <= -1:
            error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(str(co2_discount_factor)) +
                              "co2_discount_factor, should be decimal greater than -1")
        else:
            cfg_dict['co2_discount_factor'] = co2_discount_factor
    else:
        error_list.append("CONFIG FILE ERROR: co2_discount_factor is a required parameter in the config file")

    error_list, vehicle_occupancy = read_config_file_helper(cfg, cfg_type, 'analysis', 'vehicle_occupancy_car', 'REQUIRED', error_list)
    if vehicle_occupancy is not None:
        vehicle_occupancy = float(vehicle_occupancy)
        if vehicle_occupancy <= 0:
            error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(str(vehicle_occupancy)) +
                              "vehicle_occupancy_car, should be decimal greater than zero")
        else:
            cfg_dict['vehicle_occupancy'] = vehicle_occupancy
    else:
        error_list.append("CONFIG FILE ERROR: vehicle_occupancy_car is a required parameter in the config file")

    error_list, vehicle_occupancy_bus = read_config_file_helper(cfg, cfg_type, 'analysis', 'vehicle_occupancy_bus', 'OPTIONAL', error_list)
    error_list, vehicle_occupancy_light_rail = read_config_file_helper(cfg, cfg_type, 'analysis', 'vehicle_occupancy_light_rail', 'OPTIONAL', error_list)
    error_list, vehicle_occupancy_heavy_rail = read_config_file_helper(cfg, cfg_type, 'analysis', 'vehicle_occupancy_heavy_rail', 'OPTIONAL', error_list)
    if cfg_dict['calc_transit_metrics']:
        if (vehicle_occupancy_bus is None) or (vehicle_occupancy_light_rail is None) or (vehicle_occupancy_heavy_rail is None):
            error_list.append("CONFIG FILE ERROR: all vehicle occupancy rates are required parameters if calc_transit_metrics is set to 1")
        else:
            vehicle_occupancy_bus = float(vehicle_occupancy_bus)
            vehicle_occupancy_light_rail = float(vehicle_occupancy_light_rail)
            vehicle_occupancy_heavy_rail = float(vehicle_occupancy_heavy_rail)

            if vehicle_occupancy_bus <= 0:
                error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(str(vehicle_occupancy_bus)) +
                                  "vehicle_occupancy_bus, should be decimal greater than zero")
            else:
                cfg_dict['vehicle_occupancy_bus'] = vehicle_occupancy_bus

            if vehicle_occupancy_light_rail <= 0:
                error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(str(vehicle_occupancy_light_rail)) +
                                  "vehicle_occupancy_light_rail, should be decimal greater than zero")
            else:
                cfg_dict['vehicle_occupancy_light_rail'] = vehicle_occupancy_light_rail

            if vehicle_occupancy_heavy_rail <= 0:
                error_list.append("CONFIG FILE ERROR: {} is an invalid value for ".format(str(vehicle_occupancy_heavy_rail)) +
                                  "vehicle_occupancy_heavy_rail, should be decimal greater than zero")
            else:
                cfg_dict['vehicle_occupancy_heavy_rail'] = vehicle_occupancy_heavy_rail
    else:
        cfg_dict['vehicle_occupancy_bus'] = None
        cfg_dict['vehicle_occupancy_light_rail'] = None
        cfg_dict['vehicle_occupancy_heavy_rail'] = None

    error_list, veh_oper_cost = read_config_file_helper(cfg, cfg_type, 'analysis', 'veh_oper_cost_car', 'REQUIRED', error_list)
    if veh_oper_cost is not None:
        cfg_dict['veh_oper_cost'] = float(veh_oper_cost.replace('$', '').replace(',', ''))
    else:
        error_list.append("CONFIG FILE ERROR: veh_oper_cost_car is a required parameter in the config file")

    error_list, veh_oper_cost_bus = read_config_file_helper(cfg, cfg_type, 'analysis', 'veh_oper_cost_bus', 'OPTIONAL', error_list)
    error_list, veh_oper_cost_light_rail = read_config_file_helper(cfg, cfg_type, 'analysis', 'veh_oper_cost_light_rail', 'OPTIONAL', error_list)
    error_list, veh_oper_cost_heavy_rail = read_config_file_helper(cfg, cfg_type, 'analysis', 'veh_oper_cost_heavy_rail', 'OPTIONAL', error_list)
    if cfg_dict['calc_transit_metrics']:
        if (veh_oper_cost_bus is None) or (veh_oper_cost_light_rail is None) or (veh_oper_cost_heavy_rail is None):
            error_list.append("CONFIG FILE ERROR: all vehicle operating costs are required parameters if calc_transit_metrics is set to 1")
        else:
            cfg_dict['veh_oper_cost_bus'] = float(veh_oper_cost_bus.replace('$', '').replace(',', ''))
            cfg_dict['veh_oper_cost_light_rail'] = float(veh_oper_cost_light_rail.replace('$', '').replace(',', ''))
            cfg_dict['veh_oper_cost_heavy_rail'] = float(veh_oper_cost_heavy_rail.replace('$', '').replace(',', ''))
    else:
        cfg_dict['veh_oper_cost_bus'] = None
        cfg_dict['veh_oper_cost_light_rail'] = None
        cfg_dict['veh_oper_cost_heavy_rail'] = None

    error_list, vot_per_hour = read_config_file_helper(cfg, cfg_type, 'analysis', 'vot_per_hour', 'REQUIRED', error_list)
    if vot_per_hour is not None:
        cfg_dict['vot_per_hour'] = float(vot_per_hour.replace('$', '').replace(',', ''))
    else:
        error_list.append("CONFIG FILE ERROR: vot_per_hour is a required parameter in the config file")

    error_list, vot_wait_per_hour = read_config_file_helper(cfg, cfg_type, 'analysis', 'vot_wait_per_hour', 'OPTIONAL', error_list)
    if cfg_dict['calc_transit_metrics']:
        if vot_wait_per_hour is not None:
            cfg_dict['vot_wait_per_hour'] = float(vot_wait_per_hour.replace('$', '').replace(',', ''))
        else:
            error_list.append("CONFIG FILE ERROR: vot_wait_per_hour is a required parameter if calc_transit_metrics is set to 1")
    else:
        cfg_dict['vot_wait_per_hour'] = None

    error_list, transit_fare = read_config_file_helper(cfg, cfg_type, 'analysis', 'transit_fare', 'OPTIONAL', error_list)
    if cfg_dict['calc_transit_metrics']:
        if transit_fare is not None:
            cfg_dict['transit_fare'] = float(transit_fare.replace('$', '').replace(',', ''))
        else:
            error_list.append("CONFIG FILE ERROR: transit_fare is a required parameter if calc_transit_metrics is set to 1")
    else:
        cfg_dict['transit_fare'] = None

    # Annual maintenance cost and redeployment parameters
    error_list, maintenance = read_config_file_helper(cfg, cfg_type, 'analysis', 'maintenance', 'OPTIONAL', error_list)
    error_list, redeployment = read_config_file_helper(cfg, cfg_type, 'analysis', 'redeployment', 'OPTIONAL', error_list)
    
    # Set default to False if maintenance is not specified
    cfg_dict['maintenance'] = False
    if maintenance is not None:
        if maintenance not in ['True', 'False']:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for maintenance, should be 'True' or 'False' (case sensitive)".format(
                    maintenance))
        else:
            if maintenance == 'True':
                cfg_dict['maintenance'] = True

    # Set default to False if redeployment is not specified
    cfg_dict['redeployment'] = False
    if redeployment is not None:
        if redeployment not in ['True', 'False']:
            error_list.append(
                "CONFIG FILE ERROR: {} is an invalid value for redeployment, should be 'True' or 'False' (case sensitive)".format(
                    redeployment))
        else:
            if redeployment == 'True':
                cfg_dict['redeployment'] = True

    # Parameters for additional benefit calculations

    # Parameters for safety costs
    error_list, safety_cost = read_config_file_helper(cfg, cfg_type, 'analysis', 'safety_cost', 'REQUIRED', error_list)
    if safety_cost is not None:
        cfg_dict['safety_cost'] = float(safety_cost.replace('$', '').replace(',', ''))
    else:
        error_list.append("CONFIG FILE ERROR: safety_cost is a required parameter in the config file")

    error_list, safety_cost_bus = read_config_file_helper(cfg, cfg_type, 'analysis', 'safety_cost_bus', 'OPTIONAL', error_list)
    if cfg_dict['calc_transit_metrics']:
        if safety_cost_bus is not None:
            cfg_dict['safety_cost_bus'] = float(safety_cost_bus.replace('$', '').replace(',', ''))
        else:
            error_list.append("CONFIG FILE ERROR: safety_cost_bus is a required parameter if calc_transit_metrics is set to 1")
    else:
        cfg_dict['safety_cost_bus'] = None

    # Parameters for noise costs
    error_list, noise_cost = read_config_file_helper(cfg, cfg_type, 'analysis', 'noise_cost', 'REQUIRED', error_list)
    if noise_cost is not None:
        cfg_dict['noise_cost'] = float(noise_cost.replace('$', '').replace(',', ''))
    else:
        error_list.append("CONFIG FILE ERROR: noise_cost is a required parameter in the config file")

    error_list, noise_cost_bus = read_config_file_helper(cfg, cfg_type, 'analysis', 'noise_cost_bus', 'OPTIONAL', error_list)
    if cfg_dict['calc_transit_metrics']:
        if noise_cost_bus is not None:
            cfg_dict['noise_cost_bus'] = float(noise_cost_bus.replace('$', '').replace(',', ''))
        else:
            error_list.append("CONFIG FILE ERROR: noise_cost_bus is a required parameter if calc_transit_metrics is set to 1")
    else:
        cfg_dict['noise_cost_bus'] = None

    # Parameters for non-CO2 costs
    error_list, non_co2_cost = read_config_file_helper(cfg, cfg_type, 'analysis', 'non_co2_cost', 'REQUIRED', error_list)
    if non_co2_cost is not None:
        cfg_dict['non_co2_cost'] = float(non_co2_cost.replace('$', '').replace(',', ''))
    else:
        error_list.append("CONFIG FILE ERROR: non_co2_cost is a required parameter in the config file")

    error_list, non_co2_cost_bus = read_config_file_helper(cfg, cfg_type, 'analysis', 'non_co2_cost_bus', 'OPTIONAL', error_list)
    if cfg_dict['calc_transit_metrics']:
        if non_co2_cost_bus is not None:
            cfg_dict['non_co2_cost_bus'] = float(non_co2_cost_bus.replace('$', '').replace(',', ''))
        else:
            error_list.append("CONFIG FILE ERROR: non_co2_cost_bus is a required parameter if calc_transit_metrics is set to 1")
    else:
        cfg_dict['non_co2_cost_bus'] = None

    # Parameters for CO2 costs
    error_list, co2_cost = read_config_file_helper(cfg, cfg_type, 'analysis', 'co2_cost', 'REQUIRED', error_list)
    if co2_cost is not None:
        cfg_dict['co2_cost'] = float(co2_cost.replace('$', '').replace(',', ''))
    else:
        error_list.append("CONFIG FILE ERROR: co2_cost is a required parameter in the config file")

    error_list, co2_cost_bus = read_config_file_helper(cfg, cfg_type, 'analysis', 'co2_cost_bus', 'OPTIONAL', error_list)
    if cfg_dict['calc_transit_metrics']:
        if co2_cost_bus is not None:
            cfg_dict['co2_cost_bus'] = float(co2_cost_bus.replace('$', '').replace(',', ''))
        else:
            error_list.append("CONFIG FILE ERROR: co2_cost_bus is a required parameter if calc_transit_metrics is set to 1")
    else:
        cfg_dict['co2_cost_bus'] = None

    # Coordinate reference system
    error_list, crs = read_config_file_helper(cfg, cfg_type, 'analysis', 'crs', 'OPTIONAL', error_list)
    if os.path.exists(os.path.join(cfg_dict['input_dir'], 'LookupTables', 'TrueShape.csv')):
        if crs is not None:
            cfg_dict['crs'] = crs
        else:
            error_list.append("CONFIG FILE ERROR: crs is a required parameter if TrueShape.csv is provided.")
    else:
        cfg_dict['crs'] = None

    # ===================
    # UI NON-CONFIG VALUES
    # ===================

    # For cfg_type == 'json', save non-config parameters to cfg_dict
    if cfg_type == 'json':
        # Hazards dataframe with columns name, fpath, dim1, dim2, prob
        if 'haz' not in cfg or not cfg['haz']:  # missing 'haz' or cfg['haz'] is empty list
            error_list.append("CONFIG FILE ERROR: Can't find 'haz' in UI-prepared config file")
        else:
            hazard_events = pd.DataFrame(cfg['haz'])
            hazard_events = hazard_events.rename(columns={"name": "Hazard Event",
                                                          "fpath": "Filename",
                                                          "dim1": "HazardDim1",
                                                          "dim2": "HazardDim2",
                                                          "prob": "Event Probability in Start Year"})
            # Hazard files are moved and renamed by UI, given hazard name as filename
            hazard_events['Filename'] = hazard_events['Hazard Event']
            hazard_events['HazardDim1'] = hazard_events['HazardDim1'].astype(str).astype(int)
            hazard_events['HazardDim2'] = hazard_events['HazardDim2'].astype(str).astype(int)
            hazard_events['Event Probability in Start Year'] = hazard_events['Event Probability in Start Year'].astype(str).astype(float)
            cfg_dict['hazards'] = hazard_events

        # Set of recovery stages
        error_list, num_stages = read_config_file_helper(cfg, cfg_type, 'common', 'num_recovery_stages', 'REQUIRED', error_list)
        num_stages = int(num_stages)
        cfg_dict['recovery_stages'] = set([str(x) for x in list(range(num_stages+1))])

        # Socioeconomic futures dataframe with columns name, fpath
        if 'ecf' not in cfg or not cfg['ecf']:  # missing 'ecf' or cfg['ecf'] is empty list
            error_list.append("CONFIG FILE ERROR: Can't find 'ecf' in UI-prepared config file")
        else:
            socios = pd.DataFrame(cfg['ecf'])
            cfg_dict['socios'] = socios.rename(columns={"name": "Economic Scenarios",
                                                        "fpath": "Filename"})

        # Set of trip elasticity values
        if 'tle' not in cfg or not cfg['tle']:  # missing 'tle' or cfg['tle'] is empty list
            error_list.append("CONFIG FILE ERROR: Can't find 'tle' in UI-prepared config file")
        else:
            elasticities = pd.DataFrame(cfg['tle'])
            cfg_dict['elasticities'] = set([float(x) for x in elasticities['value'].dropna().tolist()])
        
        # Set of event frequency factors
        if 'eff' not in cfg or not cfg['eff']:  # missing 'eff' or cfg['eff'] is empty list
            error_list.append("CONFIG FILE ERROR: Can't find 'eff' in UI-prepared config file")
        else:
            event_frequencies = pd.DataFrame(cfg['eff'])
            cfg_dict['event_frequencies'] = set([float(x) for x in event_frequencies['value'].dropna().tolist()])
        
        # Resilience projects dataframe with columns name, group
        if 'rep' not in cfg or not cfg['rep']:  # missing 'rep' or cfg['rep'] is empty list
            error_list.append("CONFIG FILE ERROR: Can't find 'rep' in UI-prepared config file")
        else:
            projects = pd.DataFrame(cfg['rep'])
            cfg_dict['projects'] = projects.rename(columns={"name": "Project ID",
                                                            "group": "Project Groups"})

        # Not using UI parameters 'go_to', 'bl', 'py', 'rd'
        # UI parameters 'net', 'nwn', 'prt', 'pri', 'byf' are already validated by the UI code

    # ===================
    # TESTING VALUES
    # ===================

    error_list, cfg_dict['seed'] = read_config_file_helper(cfg, cfg_type, 'testing', 'seed', 'OPTIONAL', error_list)

    if any('CONFIG FILE ERROR:' in x for x in str(cfg_dict.values())):
        [error_list.append(x) for x in str(cfg_dict.values()) if 'CONFIG FILE ERROR:' in x]

    return error_list, cfg_dict
