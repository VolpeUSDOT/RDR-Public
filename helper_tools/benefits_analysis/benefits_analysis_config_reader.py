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


def read_benefits_analysis_config_file(cfg_file):
    '''
    This method reads in the benefits analysis config file
    As part of the benefits analysis config file, there is a path to an existing RDR config file
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
    cfg_dict['benefits_analysis_dir'] = read_config_file_helper(cfg, 'common', 'benefits_analysis_dir', 'REQUIRED')
    if not os.path.exists(cfg_dict['benefits_analysis_dir']):
        p = Path(cfg_dict['benefits_analysis_dir'])
        p.mkdir(parents=True, exist_ok=True)
        print('Created ' + cfg_dict['benefits_analysis_dir'])

    cfg_dict['run_id'] = read_config_file_helper(cfg, 'common', 'run_id', 'REQUIRED')

    cfg_dict['TAZ_col_name'] = read_config_file_helper(cfg, 'common', 'TAZ_col_name', 'REQUIRED')

    # =====================
    # OVERLAY METHOD VALUES
    # =====================
    cfg_dict['TAZ_source'] = read_config_file_helper(cfg, 'attribute_overlay', 'TAZ_source', 'REQUIRED')

    cfg_dict['attribute_source'] = read_config_file_helper(cfg, 'attribute_overlay', 'attribute_source', 'REQUIRED')
    if not (cfg_dict['attribute_source'].strip(' ').lower() == 'censuspoverty'):
        if not os.path.exists(cfg_dict['attribute_source']):
            raise Exception("RDR CONFIG FILE ERROR: {} could not be found".format(cfg_dict['attribute_source']))
    cfg_dict['attribute_feature'] = read_config_file_helper(cfg, 'attribute_overlay', 'attribute_feature', 'REQUIRED')
    cfg_dict['attribute_crs'] = read_config_file_helper(cfg, 'attribute_overlay', 'attribute_crs', 'REQUIRED')

    cfg_dict['min_percentile_include'] = float(read_config_file_helper(cfg, 'attribute_overlay', 'min_percentile_include', 'REQUIRED'))

    cfg_dict['output_name'] = read_config_file_helper(cfg, 'attribute_overlay', 'output_name', 'REQUIRED')

    # ========================
    # BENEFITS ANALYSIS VALUES
    # ========================

    cfg_dict['path_to_RDR_config_file'] = read_config_file_helper(cfg, 'benefits_analysis', 'path_to_RDR_config_file', 'REQUIRED')
    if not os.path.exists(cfg_dict['path_to_RDR_config_file']):
        raise Exception("RDR CONFIG FILE ERROR: {} could not be found".format(cfg_dict['path_to_RDR_config_file']))

    cfg_dict['TAZ_mapping'] = read_config_file_helper(cfg, 'benefits_analysis', 'TAZ_mapping', 'REQUIRED')
    cfg_dict['TAZ_feature'] = read_config_file_helper(cfg, 'benefits_analysis', 'TAZ_feature', 'REQUIRED')
    cfg_dict['resil'] = read_config_file_helper(cfg, 'benefits_analysis', 'resil', 'REQUIRED')
    cfg_dict['hazard'] = read_config_file_helper(cfg, 'benefits_analysis', 'hazard', 'REQUIRED')
    cfg_dict['projgroup'] = read_config_file_helper(cfg, 'benefits_analysis', 'projgroup', 'REQUIRED')
    cfg_dict['socio'] = read_config_file_helper(cfg, 'benefits_analysis', 'socio', 'REQUIRED')
    cfg_dict['elasticity'] = float(read_config_file_helper(cfg, 'benefits_analysis', 'elasticity', 'REQUIRED'))
    cfg_dict['baseline'] = read_config_file_helper(cfg, 'benefits_analysis', 'baseline', 'REQUIRED')
    cfg_dict['recovery'] = read_config_file_helper(cfg, 'benefits_analysis', 'recovery', 'REQUIRED')

    run_minieq = read_config_file_helper(cfg, 'benefits_analysis', 'run_minieq', 'OPTIONAL')
    # Set default to 0 if this is not specified
    cfg_dict['run_minieq'] = 0
    if run_minieq is not None:
        run_minieq = int(run_minieq)
        if run_minieq not in [0, 1]:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for run_minieq, should be 1 or 0".format(str(run_minieq)))
        else:
            cfg_dict['run_minieq'] = run_minieq

    run_type = read_config_file_helper(cfg, 'benefits_analysis', 'run_type', 'OPTIONAL')
    # Set default to RT if this is not specified
    cfg_dict['run_type'] = 'RT'
    if run_type is not None:
        if run_type not in ['SP', 'RT']:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for run_type, should be SP or RT".format(str(run_type)))
        else:
            cfg_dict['run_type'] = run_type

    cfg_dict['largeval'] = float(read_config_file_helper(cfg, 'benefits_analysis', 'largeval', 'REQUIRED'))

    cfg_dict['pval'] = float(read_config_file_helper(cfg, 'benefits_analysis', 'pval', 'REQUIRED'))

    return cfg_dict
