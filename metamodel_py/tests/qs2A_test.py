# Functional test of Quick Start 2 A/B/C
# Run RDR Quick Start 1, keep the results, and move them into the respective example
# folders for data in A/B/C
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/qs2A_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import shutil
import pandas as pd
import pytest

test_file_location = 'qs2_files/Example_A'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def copy_qs1_generated(source, destination):
    """Copy the QS1 generated outputs into this example workspace.

    :param source: Source path.
    :param destination: Destination path.
    :returns: None. The helper copies and renames files in place.
    :rtype: None
    """
    # If destination exists, remove completely, then copy over from source again
    if os.path.exists(destination):
        shutil.rmtree(destination)

    shutil.copytree(source, destination)
    # Modify name of metamodel scenarios files
    os.rename(os.path.join(destination, 'Metamodel_scenarios_SP_future_year_QS1.csv'),
              os.path.join(destination, 'Metamodel_scenarios_SP_future_year_QS2ExA.csv'))

def call_qs2_bat():
    """Run the QS2 batch file.

    :returns: The batch-process return code.
    :rtype: int
    """
    file_path = os.path.abspath(__file__)
    is_local = file_path.startswith('C:')

    if is_local:
        bat_file = 'run_rdr_analysis.bat'
    else:
        bat_file = 'run_rdr_analysis_gh.bat'

    returncode = subprocess.call(os.path.join(file_dir_path, bat_file))
    return returncode

def test_qs2(add_sample = True):
    """Run the QS2 example integration test.

    :param add_sample: Legacy test flag kept for compatibility with pytest parameterization.
    :returns: None. The assertions fail if the QS2-A outputs are wrong.
    :rtype: None
    """
    import rdr_setup
    import rdr_supporting

    path_to_config = os.path.join(file_dir_path, 'QS2A.config')
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

    # Read outputs - Tableau prep file
    # Example A runs an analysis on a subset of uncertainty scenarios, as specified in the user input file,
    # limited to one hazard event ('haz1'), one event frequency factor (1.001), and 2 projects ('L2-7' and 'L8-9_comp')
    # Read in tableau_input_file_QS2ExA.xlsx, sort by NetBenefits_Discounted, verify that L2-7 is top-ranked ResiliencyProject

    assert os.path.exists(os.path.join(output_folder, 'tableau_input_file_QS2ExA.xlsx'))

    tableau_file = pd.read_excel(os.path.join(output_folder, 'tableau_input_file_QS2ExA.xlsx'),
                                 sheet_name='Scenarios', engine="openpyxl")

    # Should only have three ProjectNames
    proj_name_list = list(set(tableau_file.ProjectName))
    proj_name_list.sort()
    assert proj_name_list == ['L2-7 Complete Mitigation', 'L8-9 Complete Mitigation', 'No Vulnerability Projects']

    # Top ranked is L2-7
    tableau_file.sort_values(by = ['NetBenefits_Discounted'],
                             ascending=[False], inplace = True)

    tableau_file = tableau_file.reset_index().copy()
    assert tableau_file.ResiliencyProject[0] == 'L2-7'

    # Discounted cost for this project is approx 2,041,354
    assert round(tableau_file.ProjectCosts_Discounted.iloc[0]) == pytest.approx(2041354)
