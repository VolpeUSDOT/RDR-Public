# Functional test of Reference Scenario 4
# Run RDR Reference Scenario 4, evaluate outputs are as expected
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/rs4_full_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import re
import shutil
import pandas as pd

test_file_location = 'rs4_files'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def call_rs4_bat():
    is_local = list(filter(lambda x: re.match('^C', x), os.path.abspath(__file__)))

    if 'C' in is_local:
        bat_file = 'run_rdr_full.bat'
    else:
        bat_file = 'run_rdr_full_gh.bat'

    returncode = subprocess.call(os.path.join(file_dir_path, bat_file))
    return returncode

def test_rs4(add_sample = True):
    # Run RS4
    returncode = call_rs4_bat()
    assert returncode == 0

    # Find output_folder
    import rdr_setup
    import rdr_supporting

    path_to_config = os.path.join(file_dir_path, 'RS4.config')
    error_list, cfg = rdr_setup.read_config_file(path_to_config, 'config')
    assert len(error_list) == 0

    print(cfg)

    input_folder = os.path.normpath(cfg['input_dir'])
    output_folder = os.path.normpath(cfg['output_dir'])

    print("input_folder exists? {}".format(os.path.exists(input_folder)))
    print("output_folder exists? {}".format(os.path.exists(output_folder)))

    print(os.listdir(output_folder))

    # Read outputs - start with compiled runs Excel
    assert os.path.exists(os.path.join(output_folder, 'full_combos_RS4.csv'))
    assert os.path.exists(os.path.join(output_folder, 'aeq_runs/base/RS4/base01/nocar/matrices/sp_base01.omx'))
    assert os.path.exists(os.path.join(output_folder, 'AequilibraE_Runs_Compiled_RS4.xlsx'))

    compiled_runs = pd.read_excel(os.path.join(output_folder, 'AequilibraE_Runs_Compiled_RS4.xlsx'),
                                  engine="openpyxl")

    # Get the resil levels
    obs_resil_levs = compiled_runs.resil.unique()
    exp_resil_levs = ['Road', 'Rail', 'no']

    assert len(obs_resil_levs) == len(exp_resil_levs)
    assert obs_resil_levs.sort() == exp_resil_levs.sort()

    compiled_runs_sp = compiled_runs[compiled_runs['SP/RT'] == 'SP']
    obs_max_trips = compiled_runs_sp.trips.max()
    obs_max_miles = compiled_runs_sp.miles.max()
    obs_max_hours = compiled_runs_sp.hours.max()

    exp_max_trips = 100
    exp_max_miles = 237.545172
    exp_max_hours = 15.1

    assert obs_max_trips == exp_max_trips
    assert obs_max_miles == exp_max_miles
    assert obs_max_hours == exp_max_hours

    # Assess results
    assert os.path.exists(os.path.join(output_folder, 'tableau_input_file_RS4.xlsx'))

    tableau_file = pd.read_excel(os.path.join(output_folder, 'tableau_input_file_RS4.xlsx'),
                                 sheet_name='Scenarios', engine="openpyxl")

    # Should have 12 rows
    assert tableau_file.shape[0] == 12

    # After expanding scenario space, now have Assets
    proj_name_list = list(set(tableau_file.Asset))
    proj_name_list.sort()
    assert proj_name_list == ['Link20-21',
                              'Link9-10',
                              'No Asset']

    # Top ranked by net benefits is L2-7, check the recovery path and net benefits
    tableau_file = tableau_file.sort_values(by = ['NetBenefits_Discounted'],
                                            ascending=[False])
    tableau_file = tableau_file.reset_index().copy()

    assert tableau_file.ResiliencyProject[0] == 'Rail'

    # Check repair cost of transit project
    rail_repair_cost = tableau_file.RepairCleanupCostSavings[tableau_file.ResiliencyProject == 'Rail'].min()
    assert rail_repair_cost == -58676832
