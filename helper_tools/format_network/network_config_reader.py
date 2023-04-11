import os
import datetime
import configparser
from pathlib import Path


def read_config_file_helper(config, section, key, required_or_optional):

    if not config.has_option(section, key):

        if required_or_optional.upper() == 'REQUIRED':
            raise Exception("CONFIG FILE ERROR: Can't find {} in section {}".format(key, section))

        return None

    else:
        val = config.get(section, key).strip().strip("'").strip('"')

        if val == '':
            return None
        else:
            return val


def read_network_config_file(cfg_file):
    '''
    This method reads in the format network config file
    '''

    cfg_dict = {}  # return value

    if not os.path.exists(cfg_file):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_file))

    cfg = configparser.RawConfigParser()
    cfg.read(cfg_file)

    # ===========================
    # COMMON VALUES
    # ===========================

    cfg_dict['run_id'] = read_config_file_helper(cfg, 'common', 'run_name', 'REQUIRED')

    cfg_dict['output_dir'] = read_config_file_helper(cfg, 'common', 'output_dir', 'REQUIRED')

    if not os.path.exists(cfg_dict['output_dir']):
        p = Path(cfg_dict['output_dir'])
        p.mkdir(parents=True, exist_ok=True)

    # ===========================
    # CREATE TRANSIT CC VALUES
    # ===========================

    cfg_dict['road_node_csv'] = read_config_file_helper(cfg, 'transit_connector', 'road_node_csv', 'REQUIRED')
    if not os.path.exists(cfg_dict['road_node_csv']):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_dict['road_node_csv']))

    cfg_dict['road_link_csv'] = read_config_file_helper(cfg, 'transit_connector', 'road_link_csv', 'REQUIRED')
    if not os.path.exists(cfg_dict['road_link_csv']):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_dict['road_link_csv']))

    cfg_dict['transit_node_csv'] = read_config_file_helper(cfg, 'transit_connector', 'transit_node_csv', 'REQUIRED')
    if not os.path.exists(cfg_dict['transit_node_csv']):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_dict['transit_node_csv']))

    cfg_dict['transit_link_csv'] = read_config_file_helper(cfg, 'transit_connector', 'transit_link_csv', 'REQUIRED')
    if not os.path.exists(cfg_dict['transit_link_csv']):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_dict['transit_link_csv']))

    cfg_dict['TAZ_shapefile'] = read_config_file_helper(cfg, 'transit_connector', 'TAZ_shapefile', 'REQUIRED')
    if not os.path.exists(cfg_dict['TAZ_shapefile']):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_dict['TAZ_shapefile']))

    cfg_dict['search_distance'] = read_config_file_helper(cfg, 'transit_connector', 'search_distance', 'REQUIRED')

    # =============================
    # CALC TIME AND TOLL VALUES
    # =============================

    cfg_dict['node_csv'] = read_config_file_helper(cfg, 'travel_cost', 'node_csv', 'REQUIRED')
    cfg_dict['link_csv'] = read_config_file_helper(cfg, 'travel_cost', 'link_csv', 'REQUIRED')

    cfg_dict['centroid_connector_cost'] = float(read_config_file_helper(cfg, 'travel_cost', 'centroid_connector_cost', 'REQUIRED'))
    if cfg_dict['centroid_connector_cost'] <= 0:
        raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['centroid_connector_cost'])) +
                        "centroid_connector_cost, should be number greater than 0")

    include_transit = read_config_file_helper(cfg, 'travel_cost', 'include_transit', 'REQUIRED')
    cfg_dict['include_transit'] = False
    include_transit = include_transit.lower()
    if include_transit not in ['t', 'f', 'true', 'false', 'y', 'n', 'yes', 'no']:
        raise Exception("CONFIG FILE ERROR: {} is an invalid value for include_transit, should be true or false".format(include_transit))
    if include_transit in ['t', 'true', 'y', 'yes']:
        cfg_dict['include_transit'] = True

    if cfg_dict['include_transit']:
        cfg_dict['transit_fare'] = float(read_config_file_helper(cfg, 'travel_cost', 'transit_fare', 'OPTIONAL'))
        if cfg_dict['transit_fare'] <= 0:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['transit_fare'])) +
                            "transit_fare, should be number greater than 0")
        cfg_dict['bus_wait_time'] = float(read_config_file_helper(cfg, 'travel_cost', 'bus_wait_time', 'OPTIONAL'))
        if cfg_dict['bus_wait_time'] <= 0:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['bus_wait_time'])) +
                            "bus_wait_time, should be number greater than 0")
        cfg_dict['subway_wait_time'] = float(read_config_file_helper(cfg, 'travel_cost', 'subway_wait_time', 'OPTIONAL'))
        if cfg_dict['subway_wait_time'] <= 0:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['subway_wait_time'])) +
                            "subway_wait_time, should be number greater than 0")
    else:
        cfg_dict['transit_fare'] = None
        cfg_dict['bus_wait_time'] = None
        cfg_dict['subway_wait_time'] = None

    include_nocar = read_config_file_helper(cfg, 'travel_cost', 'include_nocar', 'REQUIRED')
    cfg_dict['include_nocar'] = False
    include_nocar = include_nocar.lower()
    if include_nocar not in ['t', 'f', 'true', 'false', 'y', 'n', 'yes', 'no']:
        raise Exception("CONFIG FILE ERROR: {} is an invalid value for include_nocar, should be true or false".format(include_nocar))
    if include_nocar in ['t', 'true', 'y', 'yes']:
        cfg_dict['include_nocar'] = True

    if cfg_dict['include_nocar']:
        cfg_dict['tnc_initial_cost'] = float(read_config_file_helper(cfg, 'travel_cost', 'tnc_initial_cost', 'OPTIONAL'))
        if cfg_dict['tnc_initial_cost'] <= 0:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['tnc_initial_cost'])) +
                            "tnc_initial_cost, should be number greater than 0")
        cfg_dict['tnc_cost_per_mile'] = float(read_config_file_helper(cfg, 'travel_cost', 'tnc_cost_per_mile', 'OPTIONAL'))
        if cfg_dict['tnc_cost_per_mile'] <= 0:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['tnc_cost_per_mile'])) +
                            "tnc_cost_per_mile, should be number greater than 0")
        cfg_dict['tnc_wait_time'] = float(read_config_file_helper(cfg, 'travel_cost', 'tnc_wait_time', 'OPTIONAL'))
        if cfg_dict['tnc_wait_time'] <= 0:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['tnc_wait_time'])) +
                            "tnc_wait_time, should be number greater than 0")
    else:
        cfg_dict['tnc_initial_cost'] = None
        cfg_dict['tnc_cost_per_mile'] = None
        cfg_dict['tnc_wait_time'] = None

    return cfg_dict
