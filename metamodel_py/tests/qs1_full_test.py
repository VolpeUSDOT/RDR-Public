# Functional test of Quick Start 1
# Run RDR Quick Start 1, evaluate outputs are as expected
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/qs1_full_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import pandas as pd
import pytest

test_file_location = 'qs1_files'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def call_qs1_bat():
    """Run the QS1 batch file.

    :returns: The batch-process return code.
    :rtype: int
    """
    file_path = os.path.abspath(__file__)
    is_local = file_path.startswith('C:')

    if is_local:
        bat_file = 'run_rdr_full.bat'
    else:
        bat_file = 'run_rdr_full_gh.bat'

    returncode = subprocess.call(os.path.join(file_dir_path, bat_file))
    return returncode

def test_qs1(add_sample = True):
    """Run the QS1 end-to-end integration test.

    :param add_sample: Legacy test flag kept for compatibility with pytest parameterization.
    :returns: None. The assertions fail if the QS1 scenario output is wrong.
    :rtype: None
    """
    returncode = call_qs1_bat()
    assert returncode == 0

    # Find output_folder
    import rdr_setup
    import rdr_supporting

    path_to_config = os.path.join(file_dir_path, 'QS1.config')
    error_list, cfg = rdr_setup.read_config_file(path_to_config, 'config')
    assert len(error_list) == 0

    print(cfg)

    input_folder = os.path.normpath(cfg['input_dir'])
    output_folder = os.path.normpath(cfg['output_dir'])

    print("input_folder exists? {}".format(os.path.exists(input_folder)))
    print("output_folder exists? {}".format(os.path.exists(output_folder)))

    print(os.listdir(output_folder))

    # Read outputs - start with compiled runs Excel
    assert os.path.exists(os.path.join(output_folder, 'full_combos_QS1.csv'))
    assert os.path.exists(os.path.join(output_folder, 'aeq_runs/base/QS1/standard02/matrix/matrices/sp_standard02.omx'))
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

    exp_max_trips = pytest.approx(360600.0)
    exp_max_miles = pytest.approx(1668691.3)
    exp_max_hours = pytest.approx(44831.8451335562)

    assert obs_max_trips == exp_max_trips
    assert obs_max_miles == exp_max_miles
    assert obs_max_hours == exp_max_hours
