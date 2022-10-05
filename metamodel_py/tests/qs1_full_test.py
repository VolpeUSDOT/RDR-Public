# Functional test of Quick Start 1
# Run RDR Quick Start 1, evaluate outputs are as expected
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/qs1_1full_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import re
import shutil
import pandas as pd

# is_local = list(filter(lambda x: re.match('^C', x), os.path.abspath(__file__)))
# if 'C' in is_local:
#     test_file_location = 'qs1_files'
# else:
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

def test_qs1(add_sample = True):
    # Run QS1
    returncode = call_qs1_bat()
    assert returncode == 0

    # Find output_folder
    import rdr_setup
    import rdr_supporting

    path_to_config = os.path.join(file_dir_path, 'QS1.config')
    cfg = rdr_setup.read_config_file(path_to_config)

    print(cfg)

    input_folder = os.path.normpath(cfg['input_dir'])
    output_folder = os.path.normpath(cfg['output_dir'])

    print("input_folder exists? {}".format(os.path.exists(input_folder)))
    print("output_folder exists? {}".format(os.path.exists(output_folder)))

    print(os.listdir(output_folder))

    # Read outputs - start with compiled runs Excel
    assert os.path.exists(os.path.join(output_folder, 'full_combos_QS1.csv'))
    assert os.path.exists(os.path.join(output_folder, 'aeq_runs/base/QS1/base02/matrices/sp_base02.omx'))
    assert os.path.exists(os.path.join(output_folder, 'AequilibraE_Runs_Compiled_QS1.xlsx'))

    compiled_runs = pd.read_excel(os.path.join(output_folder, 'AequilibraE_Runs_Compiled_QS1.xlsx'),
                                    engine="openpyxl")

    # Get the resil levels
    obs_resil_levs = compiled_runs.resil.unique()
    exp_resil_levs = ['L2-7', 'L8-9_comp', 'L8-9_part', 'no']

    assert len(obs_resil_levs) == len(exp_resil_levs)
    assert all([a == b for a, b in zip(obs_resil_levs, exp_resil_levs)])

    compiled_runs_sp = compiled_runs[compiled_runs['SP/RT'] == 'SP']
    obs_max_trips = compiled_runs_sp.trips.max()
    obs_max_miles = compiled_runs_sp.miles.max()
    obs_max_hours = compiled_runs_sp.hours.max()

    exp_max_trips = 360600.0
    exp_max_miles = 1789845.3
    exp_max_hours = 43562

    assert obs_max_trips == exp_max_trips
    assert obs_max_miles == exp_max_miles
    assert obs_max_hours == exp_max_hours
