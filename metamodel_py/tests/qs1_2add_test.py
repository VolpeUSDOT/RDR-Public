# Functional test of Quick Start 1
# Run RDR Quick Start 1, evaluate outputs are as expected
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/qs1_2add_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import re
import shutil

test_file_location = 'qs1_files'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def call_qs1_bat():
    is_local = list(filter(lambda x: re.match('^C', x), os.path.abspath(__file__)))

    if 'C' in is_local:
        bat_file = 'run_rdr_full.bat'
    else:
        bat_file = 'run_rdr_full_gh.bat'

    returncode = subprocess.call(os.path.join(file_dir_path, bat_file))
    return returncode

def teardown_qs1(output_folder):
    shutil.rmtree(output_folder)

def edit_config_lhs(add_sample = 2):
    # Change from   lhs_sample_additional_target = 0
    # to:           lhs_sample_additional_target = 2
    import rdr_setup

    path_to_config = os.path.join(file_dir_path, 'QS1.config')
    cfg = rdr_setup.read_config_file(path_to_config)

    # Make a copy of the original
    fn, ext = os.path.splitext(path_to_config)

    new_fn = fn + '_ORIGINAL'

    shutil.copy(path_to_config, new_fn + ext)

    print('writing updated config file')
    with open(path_to_config, 'r') as f:
        newline = []
        for line in f.readlines():
            line = line.replace('do_additional_runs = False', 'do_additional_runs = True')
            line = line.replace('lhs_sample_additional_target = 0', 'lhs_sample_additional_target = ' + str(add_sample))
            newline.append(line)

    with open(path_to_config, "w") as f:
        for line in newline:
            f.writelines(line)
        f.close()

def revert_config():
    # Find a file with _ORIGINAL.config
    # And use this as .config. Then delete _ORIGINAL version
    pattern = '_ORIGINAL'

    for root, dir, files in os.walk(file_dir_path):
        for file in files:
            if file.endswith(pattern + '.config'):
                fn, ext = os.path.splitext(file)
                orig_fn = fn.replace(pattern, '')
                shutil.copy(os.path.join(file_dir_path, file), os.path.join(file_dir_path, orig_fn + ext))
                os.remove(os.path.join(file_dir_path, file))

def test_qs1_add_sample():
    # Edit the QS1.config
    edit_config_lhs(add_sample = 3)

    # Run QS1
    returncode = call_qs1_bat()
    assert returncode == 0

    # Find output_folder
    import rdr_setup
    import rdr_supporting
    import pandas as pd

    path_to_config = os.path.join(file_dir_path, 'QS1.config')
    cfg = rdr_setup.read_config_file(path_to_config)

    output_folder = os.path.normpath(cfg['output_dir'])
    additional_runs = cfg['lhs_sample_additional_target']
    total_runs = cfg['lhs_sample_target'] + additional_runs

    # Read outputs - start with compiled runs Excel
    assert os.path.exists(os.path.join(output_folder, 'AequilibraE_LHS_Design_QS1_' + str(total_runs) + '.csv'))

    compiled_runs = pd.read_excel(os.path.join(output_folder, 'AequilibraE_Runs_Compiled_QS1.xlsx'),
                                    engine="openpyxl")

    # Get the resil levels
    obs_resil_levs = compiled_runs.resil.unique()

    exp_resil_levs = ['L2-7', 'L8-9_comp', 'L8-9_part', 'no']

    assert len(obs_resil_levs) == len(exp_resil_levs)
    assert all([a == b for a, b in zip(obs_resil_levs, exp_resil_levs)])

    # Make sure we have total_runs number of SP runs num_duration_cases
    sp_run_n = len(compiled_runs[(compiled_runs['SP/RT'] == 'SP') & (compiled_runs['Type'] == 'Disrupt')])

    assert sp_run_n == total_runs

    revert_config() # Go back to the original config file
    teardown_qs1(output_folder)
