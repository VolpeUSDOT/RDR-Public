# Functional test of Quick Start 2 A/B/C
# Run RDR Quick Start 1, keep the results, and move them into the respective example
# folders for data in A/B/C
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/qs2B_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import re
import shutil
import pandas as pd

test_file_location = 'qs2_files/Example_B'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def copy_qs1_generated(source, destination):
    """
    Copy over the generated_files directory from QS1 tests as generated_files
    """
    # If destination exists, remove completely, then copy over from source again
    if os.path.exists(destination):
        shutil.rmtree(destination)

    shutil.copytree(source, destination)
    # Modify name of metamodel scenarios files
    os.rename(os.path.join(destination, 'Metamodel_scenarios_SP_futureyear_QS1.csv'),
              os.path.join(destination, 'Metamodel_scenarios_SP_futureyear_QS2ExB.csv'))

def call_qs2_bat():
    is_local = list(filter(lambda x: re.match('^C', x), os.path.abspath(__file__)))

    if 'C' in is_local:
        bat_file = 'run_rdr_analysis.bat'
    else:
        bat_file = 'run_rdr_analysis_gh.bat'

    returncode = subprocess.call(os.path.join(file_dir_path, bat_file))
    return returncode

def test_qs2(add_sample = True):

    # Find output_folder
    import rdr_setup
    import rdr_supporting

    path_to_config = os.path.join(file_dir_path, 'QS2B.config')
    error_list, cfg = rdr_setup.read_config_file(path_to_config, 'config')
    assert len(error_list) == 0

    print(cfg)

    input_folder = os.path.normpath(cfg['input_dir'])
    output_folder = os.path.normpath(cfg['output_dir'])

    # Find QS1 generated files from output_folder
    tests_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(output_folder))))
    qs1_generated = os.path.join(tests_root, 'qs1_files', 'Data', 'generated_files')
    # Must already have generated results from QS1 and not removed
    assert os.path.exists(qs1_generated)

    # This copies all data from QS1 and renames the metamodel scenarios CSV
    copy_qs1_generated(qs1_generated, output_folder)

    print("input_folder exists? {}".format(os.path.exists(input_folder)))
    print("output_folder exists? {}".format(os.path.exists(output_folder)))

    print(os.listdir(output_folder))

    # After copying from QS1, run QS2
    returncode = call_qs2_bat()
    assert returncode == 0

    # Example B changes parameters of the recovery module to analyze more hazard recovery cases
    # (minimum duration of 2 days, maximum duration of 8 days, 4 hazard recovery cases,
    # and hazard recovery period of 50% of initial hazard event duration)
    # Read in tableau_input_file_QS2ExB.xlsx, sort by RegretAll, verify that L2-7 is top-ranked ResiliencyProject
    # Average of NetBenefits_Discounted for L2-7 should be approx 11 MM, test for benefits > 11,000,000

    assert os.path.exists(os.path.join(output_folder, 'tableau_input_file_QS2ExB.xlsx'))

    tableau_file = pd.read_excel(os.path.join(output_folder, 'tableau_input_file_QS2ExB.xlsx'),
                                 sheet_name='Scenarios', engine="openpyxl")

    # Should have 64 rows
    assert tableau_file.shape[0] == 64

    # Top ranked by net benefits is L2-7, check the recovery path and net benefits
    tableau_file.sort_values(by = ['NetBenefits_Discounted'],
                             ascending=[False], inplace = True)

    tableau_file = tableau_file.reset_index().copy()

    assert tableau_file.ResiliencyProject[0] == 'L2-7'
    # Add this test back in eventually after guarantee same recovery path labels and joining order
    # assert tableau_file.Exposurerecoverypath[0] == '2,2,1'

    # Average net benefits
    avg_net_benef = tableau_file.groupby('ResiliencyProject')['NetBenefits_Discounted'].mean().sort_values(ascending = False)
    assert avg_net_benef[0] > 11000000
