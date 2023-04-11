import os
import datetime
import configparser


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


def read_equity_config_file(cfg_file):
    '''
    This method reads in the equity config file
    As part of the equity config file, there is a path to an existing RDR config file
    That existing RDR config file has values used in TAZ_metrics.py
    '''

    cfg_dict = {}  # return value

    if not os.path.exists(cfg_file):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_file))

    cfg = configparser.RawConfigParser()
    cfg.read(cfg_file)

    # ===================
    # COMMON VALUES
    # ===================
    cfg_dict['equity_analysis_dir'] = read_config_file_helper(cfg, 'common', 'equity_analysis_dir', 'REQUIRED')
    if not os.path.exists(cfg_dict['equity_analysis_dir']):
        p = Path(cfg_dict['equity_analysis_dir'])
        p.mkdir(parents=True, exist_ok=True)
        print('Created ' + cfg_dict['equity_analysis_dir'])

    cfg_dict['run_id'] = read_config_file_helper(cfg, 'common', 'run_id', 'REQUIRED')

    # =====================
    # OVERLAY METHOD VALUES
    # =====================
    cfg_dict['TAZ_source'] = read_config_file_helper(cfg, 'equity_overlay', 'TAZ_source', 'REQUIRED')

    cfg_dict['equity_source'] = read_config_file_helper(cfg, 'equity_overlay', 'equity_source', 'REQUIRED')
    cfg_dict['equity_feature'] = read_config_file_helper(cfg, 'equity_overlay', 'equity_feature', 'REQUIRED')

    cfg_dict['min_percentile_include'] = float(read_config_file_helper(cfg, 'equity_overlay', 'min_percentile_include', 'REQUIRED'))

    cfg_dict['output_name'] = read_config_file_helper(cfg, 'equity_overlay', 'output_name', 'REQUIRED')

    # ======================
    # EQUITY ANALYSIS VALUES
    # ======================

    cfg_dict['path_to_RDR_config_file'] = read_config_file_helper(cfg, 'equity_analysis', 'path_to_RDR_config_file', 'REQUIRED')
    if not os.path.exists(cfg_dict['path_to_RDR_config_file']):
        raise Exception("RDR CONFIG FILE ERROR: {} could not be found".format(cfg_dict['path_to_RDR_config_file']))

    cfg_dict['resil'] = read_config_file_helper(cfg, 'equity_analysis', 'resil', 'REQUIRED')
    cfg_dict['hazard'] = read_config_file_helper(cfg, 'equity_analysis', 'hazard', 'REQUIRED')
    cfg_dict['projgroup'] = read_config_file_helper(cfg, 'equity_analysis', 'projgroup', 'REQUIRED')
    cfg_dict['socio'] = read_config_file_helper(cfg, 'equity_analysis', 'socio', 'REQUIRED')
    cfg_dict['elasticity'] = float(read_config_file_helper(cfg, 'equity_analysis', 'elasticity', 'REQUIRED'))
    cfg_dict['baseline'] = read_config_file_helper(cfg, 'equity_analysis', 'baseline', 'REQUIRED')
    cfg_dict['recovery'] = read_config_file_helper(cfg, 'equity_analysis', 'recovery', 'REQUIRED')

    run_minieq = read_config_file_helper(cfg, 'equity_analysis', 'run_minieq', 'OPTIONAL')
    # Set default to 1 if this is not specified
    cfg_dict['run_minieq'] = 1
    if run_minieq is not None:
        run_minieq = int(run_minieq)
        if run_minieq not in [0, 1]:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for run_minieq, should be 1 or 0".format(str(run_minieq)))
        else:
            cfg_dict['run_minieq'] = run_minieq

    cfg_dict['run_type'] = read_config_file_helper(cfg, 'equity_analysis', 'run_type', 'REQUIRED')
    cfg_dict['largeval'] = read_config_file_helper(cfg, 'equity_analysis', 'largeval', 'REQUIRED')

    return cfg_dict
