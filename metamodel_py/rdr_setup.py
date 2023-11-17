#!/usr/bin/env python
# coding: utf-8


import os
import configparser
from pathlib import Path
import re

# ==============================================================================


def read_config_file_helper(config, section, key, required_or_optional):
    if not config.has_option(section, key):
        if required_or_optional.upper() == 'REQUIRED':
            #logger.error("CONFIG FILE ERROR: Can't find {} in section {}".format(key, section))
            raise Exception("CONFIG FILE ERROR: Can't find {} in section {}".format(key, section))

        return None

    else:
        val = config.get(section, key).strip().strip("'").strip('"')

        if val == '':
            return None
        else:
            return val


# ==============================================================================


def read_config_file(cfg_file):
    cfg_dict = {}  # return value

    if not os.path.exists(cfg_file):
        #logger.error("CONFIG FILE ERROR: {} could not be found".format(cfg_file))
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_file))

    cfg = configparser.RawConfigParser()
    cfg.read(cfg_file)

    # ===================
    # COMMON VALUES
    # ===================

    cfg_dict['input_dir'] = read_config_file_helper(cfg, 'common', 'input_dir', 'REQUIRED')

    if re.search('^\\.\\\\tests', cfg_dict['input_dir']):
        cfg_dict['input_dir'] = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), cfg_dict['input_dir']))

    if not os.path.exists(cfg_dict['input_dir']):
        #logger.error("CONFIG FILE ERROR: input directory {} can't be found".format(cfg_dict['input_dir']))
        raise Exception("CONFIG FILE ERROR: input directory {} can't be found".format(cfg_dict['input_dir']))

    cfg_dict['output_dir'] = read_config_file_helper(cfg, 'common', 'output_dir', 'REQUIRED')

    if re.search('^\\.\\\\tests', cfg_dict['output_dir']):
        cfg_dict['output_dir'] = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), cfg_dict['output_dir']))

    if not os.path.exists(cfg_dict['output_dir']):
        p = Path(cfg_dict['output_dir'])
        p.mkdir(parents=True, exist_ok=True)
        print('Created ' + cfg_dict['output_dir'])

    cfg_dict['run_id'] = read_config_file_helper(cfg, 'common', 'run_id', 'REQUIRED')

    cfg_dict['start_year'] = int(read_config_file_helper(cfg, 'common', 'start_year', 'REQUIRED'))
    cfg_dict['end_year'] = int(read_config_file_helper(cfg, 'common', 'end_year', 'REQUIRED'))
    cfg_dict['base_year'] = int(read_config_file_helper(cfg, 'common', 'base_year', 'REQUIRED'))
    cfg_dict['future_year'] = int(read_config_file_helper(cfg, 'common', 'future_year', 'REQUIRED'))

    # ===================
    # METAMODEL VALUES
    # ===================

    metamodel_type = read_config_file_helper(cfg, 'metamodel', 'metamodel_type', 'OPTIONAL')
    # Set default to 'multitarget' if this is not specified
    cfg_dict['metamodel_type'] = 'multitarget'
    if metamodel_type is not None:
        if metamodel_type not in ['base', 'interact', 'projgroupLM', 'multitarget', 'mixedeffects']:
            #logger.error("CONFIG FILE ERROR: {} is an invalid value for metamodel_type, see config file for possible options (case sensitive)".format(
            #        metamodel_type))
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for metamodel_type, see config file for possible options (case sensitive)".format(
                    metamodel_type))
        else:
            cfg_dict['metamodel_type'] = metamodel_type

    cfg_dict['lhs_sample_target'] = int(read_config_file_helper(cfg, 'metamodel', 'lhs_sample_target', 'REQUIRED'))

    do_additional_runs = read_config_file_helper(cfg, 'metamodel', 'do_additional_runs', 'OPTIONAL')
    # Set default to False if this is not specified
    cfg_dict['do_additional_runs'] = 'False'
    if do_additional_runs is not None:
        if do_additional_runs not in ['True', 'False']:
            #logger.error("CONFIG FILE ERROR: {} is an invalid value for do_additional_runs, should be 'True' or 'False' (case sensitive)".format(
            #        do_additional_runs))
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for do_additional_runs, should be 'True' or 'False' (case sensitive)".format(
                    do_additional_runs))
        else:
            cfg_dict['do_additional_runs'] = do_additional_runs

    lhs_sample_additional_target = read_config_file_helper(cfg, 'metamodel', 'lhs_sample_additional_target', 'OPTIONAL')
    if lhs_sample_additional_target is not None:
        cfg_dict['lhs_sample_additional_target'] = int(lhs_sample_additional_target)
        if cfg_dict['do_additional_runs'] == 'True':
            if cfg_dict['lhs_sample_additional_target'] == 0:
                #logger.error("CONFIG FILE ERROR: A positive value for lhs_sample_additional_target is required since do_additional_runs = 'True'")
                raise Exception("CONFIG FILE ERROR: A positive value for lhs_sample_additional_target is required since do_additional_runs = 'True'")
    else:
        if cfg_dict['do_additional_runs'] == 'True':
            #logger.error("CONFIG FILE ERROR: A positive value for lhs_sample_additional_target is required since do_additional_runs = 'True'")
            raise Exception("CONFIG FILE ERROR: A positive value for lhs_sample_additional_target is required since do_additional_runs = 'True'")

    aeq_run_type = read_config_file_helper(cfg, 'metamodel', 'aeq_run_type', 'OPTIONAL')
    # Set default to routing if this is not specified
    cfg_dict['aeq_run_type'] = 'RT'
    if aeq_run_type is not None:
        aeq_run_type = aeq_run_type.upper()
        if aeq_run_type not in ['SP', 'RT']:
            #logger.error("CONFIG FILE ERROR: {} is an invalid value for aeq_run_type, should be 'SP' or 'RT'".format(
            #        aeq_run_type))
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for aeq_run_type, should be 'SP' or 'RT'".format(
                    aeq_run_type))
        else:
            cfg_dict['aeq_run_type'] = aeq_run_type

    run_minieq = read_config_file_helper(cfg, 'metamodel', 'run_minieq', 'OPTIONAL')
    # Set default to 0 if this is not specified
    cfg_dict['run_minieq'] = 0
    if run_minieq is not None:
        run_minieq = int(run_minieq)
        if run_minieq not in [0, 1]:
            #logger.error(
            #    "CONFIG FILE ERROR: {} is an invalid value for run_minieq, should be 1 or 0".format(str(run_minieq)))
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for run_minieq, should be 1 or 0".format(str(run_minieq)))
        else:
            cfg_dict['run_minieq'] = run_minieq

    allow_centroid_flows = read_config_file_helper(cfg, 'metamodel', 'allow_centroid_flows', 'OPTIONAL')
    # Note that parameter used by AequilibraE is blocked_centroid_flows as T/F so translate config parameter accordingly
    # Set default to False if this is not specified
    cfg_dict['blocked_centroid_flows'] = False
    if allow_centroid_flows is not None:
        allow_centroid_flows = int(allow_centroid_flows)
        if allow_centroid_flows not in [0, 1]:
            #logger.error(
            #    "CONFIG FILE ERROR: {} is an invalid value for allow_centroid_flows, should be 1 or 0".format(str(allow_centroid_flows)))
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for allow_centroid_flows, should be 1 or 0".format(str(allow_centroid_flows)))
        else:
            if allow_centroid_flows == 0:
                cfg_dict['blocked_centroid_flows'] = True

    calc_transit_metrics = read_config_file_helper(cfg, 'metamodel', 'calc_transit_metrics', 'OPTIONAL')
    # Translate config parameter into T/F
    # Set default to True if this is not specified
    cfg_dict['calc_transit_metrics'] = True
    if calc_transit_metrics is not None:
        calc_transit_metrics = int(calc_transit_metrics)
        if calc_transit_metrics not in [0, 1]:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for calc_transit_metrics, should be 1 or 0".format(str(calc_transit_metrics)))
        else:
            if calc_transit_metrics == 0:
                cfg_dict['calc_transit_metrics'] = False

    if cfg_dict['calc_transit_metrics'] and cfg_dict['aeq_run_type'] == 'SP':
        raise Exception("CONFIG FILE ERROR: aeq_run_type must be set to 'RT' if calc_transit_metrics is set to 1")

    # ===================
    # DISRUPTION VALUES
    # ===================

    link_availability_approach = read_config_file_helper(cfg, 'disruption', 'link_availability_approach', 'OPTIONAL')
    # Set default to binary if this is not specified
    cfg_dict['link_availability_approach'] = 'binary'
    if link_availability_approach is not None:
        link_availability_approach = link_availability_approach.lower()
        if link_availability_approach not in ['binary', 'default_flood_exposure_function', 'manual',
                                              'beta_distribution_function']:
            #logger.error(
            #    "CONFIG FILE ERROR: {} is an invalid value for link_availability_approach, ".format(link_availability_approach) +
            #    "should be 'binary', 'default_flood_exposure_function', 'beta_distribution_function', or 'manual'")
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for link_availability_approach, ".format(link_availability_approach) +
                "should be 'binary', 'default_flood_exposure_function', 'beta_distribution_function', or 'manual'")
        else:
            cfg_dict['link_availability_approach'] = link_availability_approach

    cfg_dict['exposure_field'] = read_config_file_helper(cfg, 'disruption', 'exposure_field', 'REQUIRED')

    # See Recovery section below for definition of exposure unit parameter used by both disruption and recovery modules

    if cfg_dict['link_availability_approach'] == 'manual':
        cfg_dict['link_availability_csv'] = read_config_file_helper(cfg, 'disruption', 'link_availability_csv', 'REQUIRED')
    else:
        cfg_dict['link_availability_csv'] = None

    if cfg_dict['link_availability_approach'] == 'beta_distribution_function':
        cfg_dict['alpha'] = float(read_config_file_helper(cfg, 'disruption', 'alpha', 'REQUIRED'))
        if cfg_dict['alpha'] <= 0:
            #logger.error("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['alpha'])) +
            #                "alpha, should be number greater than 0")
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['alpha'])) +
                            "alpha, should be number greater than 0")
        cfg_dict['beta'] = float(read_config_file_helper(cfg, 'disruption', 'beta', 'REQUIRED'))
        if cfg_dict['beta'] <= 0:
            #logger.error("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['beta'])) +
            #                "beta, should be number greater than 0")
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['beta'])) +
                            "beta, should be number greater than 0")
        cfg_dict['lower_bound'] = float(read_config_file_helper(cfg, 'disruption', 'lower_bound', 'REQUIRED'))
        cfg_dict['upper_bound'] = float(read_config_file_helper(cfg, 'disruption', 'upper_bound', 'REQUIRED'))
        cfg_dict['beta_method'] = read_config_file_helper(cfg, 'disruption', 'beta_method', 'REQUIRED')
        if cfg_dict['beta_method'] not in ['lower cumulative', 'upper cumulative']:
            #logger.error(
            #    "CONFIG FILE ERROR: {} is an invalid value for beta_method, ".format(cfg_dict['beta_method']) +
            #    "should be 'lower cumulative' or 'upper cumulative' (case sensitive)")
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for beta_method, ".format(cfg_dict['beta_method']) +
                "should be 'lower cumulative' or 'upper cumulative' (case sensitive)")
    else:
        cfg_dict['alpha'] = None
        cfg_dict['beta'] = None
        cfg_dict['lower_bound'] = None
        cfg_dict['upper_bound'] = None
        cfg_dict['beta_method'] = None

    zone_conn = read_config_file_helper(cfg, 'disruption', 'highest_zone_number', 'OPTIONAL')
    # Set default to 0 if this is not specified
    cfg_dict['zone_conn'] = 0
    if zone_conn is not None:
        zone_conn = int(zone_conn)
        if zone_conn < 0:
            #logger.error("CONFIG FILE ERROR: {} is an invalid value for ".format(str(zone_conn)) +
            #                "highest_zone_number, should be integer greater than or equal to 0")
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(zone_conn)) +
                            "highest_zone_number, should be integer greater than or equal to 0")
        else:
            cfg_dict['zone_conn'] = zone_conn

    resil_mitigation_approach = read_config_file_helper(cfg, 'disruption', 'resil_mitigation_approach', 'OPTIONAL')
    # Set default to binary if this is not specified
    cfg_dict['resil_mitigation_approach'] = 'binary'
    if resil_mitigation_approach is not None:
        resil_mitigation_approach = resil_mitigation_approach.lower()
        if resil_mitigation_approach not in ['binary', 'manual']:
            #logger.error(
            #    "CONFIG FILE ERROR: {} is an invalid value for ".format(resil_mitigation_approach) +
            #    "resil_mitigation_approach, should be 'binary' or 'manual'")
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for ".format(resil_mitigation_approach) +
                "resil_mitigation_approach, should be 'binary' or 'manual'")
        else:
            cfg_dict['resil_mitigation_approach'] = resil_mitigation_approach

    # ===================
    # RECOVERY VALUES
    # ===================

    cfg_dict['min_duration'] = float(read_config_file_helper(cfg, 'recovery', 'min_duration', 'REQUIRED'))
    cfg_dict['max_duration'] = float(read_config_file_helper(cfg, 'recovery', 'max_duration', 'REQUIRED'))
    cfg_dict['num_duration_cases'] = int(read_config_file_helper(cfg, 'recovery', 'num_duration_cases', 'REQUIRED'))

    cfg_dict['hazard_recov_type'] = read_config_file_helper(cfg, 'recovery', 'hazard_recov_type', 'REQUIRED')
    if cfg_dict['hazard_recov_type'] not in ['days', 'percent']:
        #logger.error("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['hazard_recov_type']) +
        #                "hazard_recov_type, should be 'days' or 'percent' (case sensitive)")
        raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['hazard_recov_type']) +
                        "hazard_recov_type, should be 'days' or 'percent' (case sensitive)")

    hazard_recov_length = read_config_file_helper(cfg, 'recovery', 'hazard_recov_length', 'REQUIRED')
    if cfg_dict['hazard_recov_type'] == 'days':
        cfg_dict['hazard_recov_length'] = float(hazard_recov_length)

    if cfg_dict['hazard_recov_type'] == 'percent':
        cfg_dict['hazard_recov_length'] = float(hazard_recov_length.strip('%'))/100

    cfg_dict['hazard_recov_path_model'] = read_config_file_helper(cfg, 'recovery', 'hazard_recov_path_model',
                                                                  'REQUIRED').lower()
    if cfg_dict['hazard_recov_path_model'] not in ['equal']:
        #logger.error("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['hazard_recov_path_model']) +
        #                "hazard_recov_path_model, should be 'Equal'")
        raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['hazard_recov_path_model']) +
                        "hazard_recov_path_model, should be 'Equal'")

    exposure_damage_approach = read_config_file_helper(cfg, 'recovery', 'exposure_damage_approach', 'OPTIONAL')
    # Set default to binary if this is not specified
    cfg_dict['exposure_damage_approach'] = 'binary'
    if exposure_damage_approach is not None:
        exposure_damage_approach = exposure_damage_approach.lower()
        if exposure_damage_approach not in ['binary', 'default_damage_table', 'manual']:
            #logger.error(
            #    "CONFIG FILE ERROR: {} is an invalid value for ".format(exposure_damage_approach) +
            #    "exposure_damage_approach, should be 'binary', 'default_damage_table', or 'manual'")
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for ".format(exposure_damage_approach) +
                "exposure_damage_approach, should be 'binary', 'default_damage_table', or 'manual'")
        else:
            cfg_dict['exposure_damage_approach'] = exposure_damage_approach

    # Set units of exposure if default flood exposure function or default depth-damage table is chosen
    # NOTE: need both cfg_dict['link_availability_approach'] and cfg_dict['exposure_damage_approach'] to be defined already
    if cfg_dict['link_availability_approach'] == 'default_flood_exposure_function' or cfg_dict['exposure_damage_approach'] == 'default_damage_table':
        cfg_dict['exposure_unit'] = read_config_file_helper(cfg, 'disruption', 'exposure_unit', 'REQUIRED')
        if cfg_dict['exposure_unit'].lower() not in ['feet', 'foot', 'ft', 'yards', 'yard', 'm', 'meters']:
            #logger.error(
            #    "CONFIG FILE ERROR: {} is an invalid value for exposure_unit, ".format(cfg_dict['exposure_unit']) +
            #    "the default flood exposure function and default damage table are currently only compatible with " +
            #    "depths provided in 'feet', 'yards', or 'meters'")
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for exposure_unit, ".format(cfg_dict['exposure_unit']) +
                "the default flood exposure function and default damage table are currently only compatible with " +
                "depths provided in 'feet', 'yards', or 'meters'")
    else:
        cfg_dict['exposure_unit'] = None

    if cfg_dict['exposure_damage_approach'] == 'manual':
        cfg_dict['exposure_damage_csv'] = read_config_file_helper(cfg, 'recovery', 'exposure_damage_csv', 'REQUIRED')
    else:
        cfg_dict['exposure_damage_csv'] = None

    cfg_dict['repair_cost_approach'] = read_config_file_helper(cfg, 'recovery', 'repair_cost_approach',
                                                               'REQUIRED').lower()
    if cfg_dict['repair_cost_approach'] not in ['default', 'user-defined']:
        #logger.error("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['repair_cost_approach']) +
        #                "repair_cost_approach, should be 'default' or 'user-defined'")
        raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['repair_cost_approach']) +
                        "repair_cost_approach, should be 'default' or 'user-defined'")

    # Set network type if default repair cost table is chosen
    if cfg_dict['repair_cost_approach'] == 'default':
        cfg_dict['repair_network_type'] = read_config_file_helper(cfg, 'recovery', 'repair_network_type', 'REQUIRED')
        if cfg_dict['repair_network_type'] not in ['Rural Flat', 'Rural Rolling', 'Rural Mountainous', 'Small Urban',
                                                   'Small Urbanized', 'Large Urbanized', 'Major Urbanized']:
            #logger.error("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['repair_network_type']) +
            #                "repair_network_type, see config file for possible options (case sensitive)")
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['repair_network_type']) +
                            "repair_network_type, see config file for possible options (case sensitive)")
    else:
        cfg_dict['repair_network_type'] = None

    if cfg_dict['repair_cost_approach'] == 'user-defined':
        cfg_dict['repair_cost_csv'] = read_config_file_helper(cfg, 'recovery', 'repair_cost_csv', 'REQUIRED')
    else:
        cfg_dict['repair_cost_csv'] = None

    cfg_dict['repair_time_approach'] = read_config_file_helper(cfg, 'recovery', 'repair_time_approach',
                                                               'REQUIRED').lower()
    if cfg_dict['repair_time_approach'] not in ['default', 'user-defined']:
        #logger.error("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['repair_time_approach']) +
        #                "repair_time_approach, should be 'default' or 'user-defined'")
        raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(cfg_dict['repair_time_approach']) +
                        "repair_time_approach, should be 'default' or 'user-defined'")

    if cfg_dict['repair_time_approach'] == 'user-defined':
        cfg_dict['repair_time_csv'] = read_config_file_helper(cfg, 'recovery', 'repair_time_csv', 'REQUIRED')
    else:
        cfg_dict['repair_time_csv'] = None

    # ===================
    # ANALYSIS VALUES
    # ===================

    roi_analysis_type = read_config_file_helper(cfg, 'analysis', 'roi_analysis_type', 'REQUIRED')
    if roi_analysis_type not in ['BCA', 'Regret', 'Breakeven']:
        #logger.error(
        #    "CONFIG FILE ERROR: {} is an invalid value for roi_analysis_type, see config file for possible options (case sensitive)".format(
        #        roi_analysis_type))
        raise Exception(
            "CONFIG FILE ERROR: {} is an invalid value for roi_analysis_type, see config file for possible options (case sensitive)".format(
                roi_analysis_type))
    else:
        cfg_dict['roi_analysis_type'] = roi_analysis_type

    cfg_dict['dollar_year'] = int(read_config_file_helper(cfg, 'analysis', 'dollar_year', 'REQUIRED'))

    discount_factor = read_config_file_helper(cfg, 'analysis', 'discount_factor', 'REQUIRED')
    if discount_factor is not None:
        discount_factor = float(discount_factor)
        if discount_factor <= -1:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(discount_factor)) +
                            "discount_factor, should be decimal greater than -1")
        else:
            cfg_dict['discount_factor'] = discount_factor
    else:
        raise Exception("CONFIG FILE ERROR: discount_factor is a required parameter in the config file")

    co2_discount_factor = read_config_file_helper(cfg, 'analysis', 'co2_discount_factor', 'REQUIRED')
    if co2_discount_factor is not None:
        co2_discount_factor = float(co2_discount_factor)
        if co2_discount_factor <= -1:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(co2_discount_factor)) +
                            "co2_discount_factor, should be decimal greater than -1")
        else:
            cfg_dict['co2_discount_factor'] = co2_discount_factor
    else:
        raise Exception("CONFIG FILE ERROR: co2_discount_factor is a required parameter in the config file")

    vehicle_occupancy = read_config_file_helper(cfg, 'analysis', 'vehicle_occupancy_car', 'REQUIRED')
    if vehicle_occupancy is not None:
        vehicle_occupancy = float(vehicle_occupancy)
        if vehicle_occupancy <= 0:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(vehicle_occupancy)) +
                            "vehicle_occupancy_car, should be decimal greater than zero")
        else:
            cfg_dict['vehicle_occupancy'] = vehicle_occupancy
    else:
        raise Exception("CONFIG FILE ERROR: vehicle_occupancy_car is a required parameter in the config file")

    vehicle_occupancy_bus = read_config_file_helper(cfg, 'analysis', 'vehicle_occupancy_bus', 'OPTIONAL')
    vehicle_occupancy_light_rail = read_config_file_helper(cfg, 'analysis', 'vehicle_occupancy_light_rail', 'OPTIONAL')
    vehicle_occupancy_heavy_rail = read_config_file_helper(cfg, 'analysis', 'vehicle_occupancy_heavy_rail', 'OPTIONAL')
    if cfg_dict['calc_transit_metrics']:
        if (vehicle_occupancy_bus is None) or (vehicle_occupancy_light_rail is None) or (vehicle_occupancy_heavy_rail is None):
            raise Exception("CONFIG FILE ERROR: all vehicle occupancy rates are required parameters if calc_transit_metrics is set to 1")
        else:
            vehicle_occupancy_bus = float(vehicle_occupancy_bus)
            vehicle_occupancy_light_rail = float(vehicle_occupancy_light_rail)
            vehicle_occupancy_heavy_rail = float(vehicle_occupancy_heavy_rail)

            if vehicle_occupancy_bus <= 0:
                raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(vehicle_occupancy_bus)) +
                                "vehicle_occupancy_bus, should be decimal greater than zero")
            else:
                cfg_dict['vehicle_occupancy_bus'] = vehicle_occupancy_bus

            if vehicle_occupancy_light_rail <= 0:
                raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(vehicle_occupancy_light_rail)) +
                                "vehicle_occupancy_light_rail, should be decimal greater than zero")
            else:
                cfg_dict['vehicle_occupancy_light_rail'] = vehicle_occupancy_light_rail

            if vehicle_occupancy_heavy_rail <= 0:
                raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(vehicle_occupancy_heavy_rail)) +
                                "vehicle_occupancy_heavy_rail, should be decimal greater than zero")
            else:
                cfg_dict['vehicle_occupancy_heavy_rail'] = vehicle_occupancy_heavy_rail

    veh_oper_cost = read_config_file_helper(cfg, 'analysis', 'veh_oper_cost_car', 'REQUIRED')
    if veh_oper_cost is not None:
        cfg_dict['veh_oper_cost'] = float(veh_oper_cost.replace('$', '').replace(',', ''))
    else:
        raise Exception("CONFIG FILE ERROR: veh_oper_cost_car is a required parameter in the config file")

    veh_oper_cost_bus = read_config_file_helper(cfg, 'analysis', 'veh_oper_cost_bus', 'OPTIONAL')
    veh_oper_cost_light_rail = read_config_file_helper(cfg, 'analysis', 'veh_oper_cost_light_rail', 'OPTIONAL')
    veh_oper_cost_heavy_rail = read_config_file_helper(cfg, 'analysis', 'veh_oper_cost_heavy_rail', 'OPTIONAL')
    if cfg_dict['calc_transit_metrics']:
        if (veh_oper_cost_bus is None) or (veh_oper_cost_light_rail is None) or (veh_oper_cost_heavy_rail is None):
            raise Exception("CONFIG FILE ERROR: all vehicle operating costs are required parameters if calc_transit_metrics is set to 1")
        else:
            cfg_dict['veh_oper_cost_bus'] = float(veh_oper_cost_bus.replace('$', '').replace(',', ''))
            cfg_dict['veh_oper_cost_light_rail'] = float(veh_oper_cost_light_rail.replace('$', '').replace(',', ''))
            cfg_dict['veh_oper_cost_heavy_rail'] = float(veh_oper_cost_heavy_rail.replace('$', '').replace(',', ''))

    vot_per_hour = read_config_file_helper(cfg, 'analysis', 'vot_per_hour', 'REQUIRED')
    if vot_per_hour is not None:
        cfg_dict['vot_per_hour'] = float(vot_per_hour.replace('$', '').replace(',', ''))
    else:
        raise Exception("CONFIG FILE ERROR: vot_per_hour is a required parameter in the config file")

    vot_wait_per_hour = read_config_file_helper(cfg, 'analysis', 'vot_wait_per_hour', 'OPTIONAL')
    if cfg_dict['calc_transit_metrics']:
        if vot_wait_per_hour is not None:
            cfg_dict['vot_wait_per_hour'] = float(vot_wait_per_hour.replace('$', '').replace(',', ''))
        else:
            raise Exception("CONFIG FILE ERROR: vot_wait_per_hour is a required parameter if calc_transit_metrics is set to 1")

    transit_fare = read_config_file_helper(cfg, 'analysis', 'transit_fare', 'OPTIONAL')
    if cfg_dict['calc_transit_metrics']:
        if transit_fare is not None:
            cfg_dict['transit_fare'] = float(transit_fare.replace('$', '').replace(',', ''))
        else:
            raise Exception("CONFIG FILE ERROR: transit_fare is a required parameter if calc_transit_metrics is set to 1")

    # Annual maintenance cost and redeployment parameters
    maintenance = read_config_file_helper(cfg, 'analysis', 'maintenance', 'OPTIONAL')
    redeployment = read_config_file_helper(cfg, 'analysis', 'redeployment', 'OPTIONAL')
    
    # Set default to False if maintenance is not specified
    cfg_dict['maintenance'] = False
    if maintenance is not None:
        if maintenance not in ['True', 'False']:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for maintenance, should be 'True' or 'False' (case sensitive)".format(
                    maintenance))
        else:
            if maintenance == 'True':
                cfg_dict['maintenance'] = True

    # Set default to False if redeployment is not specified
    cfg_dict['redeployment'] = False
    if redeployment is not None:
        if redeployment not in ['True', 'False']:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for redeployment, should be 'True' or 'False' (case sensitive)".format(
                    redeployment))
        else:
            if redeployment == 'True':
                cfg_dict['redeployment'] = True

    # Parameters for additional benefit calculations

    # Parameters for safety costs
    safety_cost = read_config_file_helper(cfg, 'analysis', 'safety_cost', 'REQUIRED')
    if safety_cost is not None:
        cfg_dict['safety_cost'] = float(safety_cost.replace('$', '').replace(',', ''))
    else:
        raise Exception("CONFIG FILE ERROR: safety_cost is a required parameter in the config file")

    safety_cost_bus = read_config_file_helper(cfg, 'analysis', 'safety_cost_bus', 'OPTIONAL')
    if cfg_dict['calc_transit_metrics']:
        if safety_cost_bus is not None:
            cfg_dict['safety_cost_bus'] = float(safety_cost_bus.replace('$', '').replace(',', ''))
        else:
            raise Exception("CONFIG FILE ERROR: safety_cost_bus is a required parameter if calc_transit_metrics is set to 1")

    # Parameters for noise costs
    noise_cost = read_config_file_helper(cfg, 'analysis', 'noise_cost', 'REQUIRED')
    if noise_cost is not None:
        cfg_dict['noise_cost'] = float(noise_cost.replace('$', '').replace(',', ''))
    else:
        raise Exception("CONFIG FILE ERROR: noise_cost is a required parameter in the config file")

    noise_cost_bus = read_config_file_helper(cfg, 'analysis', 'noise_cost_bus', 'OPTIONAL')
    if cfg_dict['calc_transit_metrics']:
        if noise_cost_bus is not None:
            cfg_dict['noise_cost_bus'] = float(noise_cost_bus.replace('$', '').replace(',', ''))
        else:
            raise Exception("CONFIG FILE ERROR: noise_cost_bus is a required parameter if calc_transit_metrics is set to 1")

    # Parameters for CO2/NOX/SO2/PM2.5 emission rates
    cfg_dict['co2_rate'] = float(read_config_file_helper(cfg, 'analysis', 'co2_rate', 'REQUIRED'))
    cfg_dict['nox_rate'] = float(read_config_file_helper(cfg, 'analysis', 'nox_rate', 'REQUIRED'))
    cfg_dict['so2_rate'] = float(read_config_file_helper(cfg, 'analysis', 'so2_rate', 'REQUIRED'))
    cfg_dict['pm25_rate'] = float(read_config_file_helper(cfg, 'analysis', 'pm25_rate', 'REQUIRED'))
    # Note: parameters only exist if calc_transit_metrics is True
    if cfg_dict['calc_transit_metrics']:
        cfg_dict['co2_rate_bus'] = float(read_config_file_helper(cfg, 'analysis', 'co2_rate_bus', 'REQUIRED'))
        cfg_dict['nox_rate_bus'] = float(read_config_file_helper(cfg, 'analysis', 'nox_rate_bus', 'REQUIRED'))
        cfg_dict['so2_rate_bus'] = float(read_config_file_helper(cfg, 'analysis', 'so2_rate_bus', 'REQUIRED'))
        cfg_dict['pm25_rate_bus'] = float(read_config_file_helper(cfg, 'analysis', 'pm25_rate_bus', 'REQUIRED'))

    # Parameter for emissions monetization CSV table
    # If blank set to default location in config folder
    emissions_monetization_csv = read_config_file_helper(cfg, 'analysis', 'emissions_monetization_csv', 'OPTIONAL')
    if emissions_monetization_csv is not None:
        cfg_dict['emissions_monetization_csv'] = emissions_monetization_csv
    else:
        # Set default to binary if this is not specified
        cfg_dict['emissions_monetization_csv'] = os.path.join(os.path.abspath(os.path.join(os.getcwd(), os.pardir)),
                                                              'config', 'default_emissions-monetization_table.csv')

    # ===================
    # TESTING VALUES
    # ===================

    cfg_dict['seed'] = read_config_file_helper(cfg, 'testing', 'seed', 'OPTIONAL')

    return cfg_dict
