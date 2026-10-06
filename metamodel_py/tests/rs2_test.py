# Functional test of Reference Scenario 2
# Run RDR Quick Start 1, keep the results, and move them into the respective example
# folders for data in RS2
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/rs2_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import shutil
import pandas as pd

test_file_location = 'rs2_files'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def copy_qs1_generated(source, destination):
    """Copy the QS1 generated outputs into the RS2 workspace.

    :param source: Source path.
    :param destination: Destination path.
    :returns: None. The helper copies files in place.
    :rtype: None
    """
    # If destination exists, remove completely, then copy over from source again
    if os.path.exists(destination):
        shutil.rmtree(destination)

    shutil.copytree(source, destination)

def call_rs2_bat():
    """Run the RS2 batch file.

    :returns: The batch-process return code.
    :rtype: int
    """
    file_path = os.path.abspath(__file__)
    is_local = file_path.startswith('C:')

    if is_local:
        bat_file = 'run_rdr_full.bat'
    else:
        bat_file = 'run_rdr_full_gh.bat'

    ps = subprocess.Popen(('echo', 'r'), stdout=subprocess.PIPE, shell=True)
    returncode = subprocess.call(os.path.join(file_dir_path, bat_file), stdin=ps.stdout)
    return returncode

def test_rs2(add_sample = True):
    """Run the RS2 integration test.

    :param add_sample: Legacy test flag kept for compatibility with pytest parameterization.
    :returns: None. The assertions fail if the RS2 outputs are wrong.
    :rtype: None
    """
    import rdr_setup
    import rdr_supporting

    path_to_config = os.path.join(file_dir_path, 'RS2.config')
    error_list, cfg = rdr_setup.read_config_file(path_to_config, 'config')
    assert len(error_list) == 0

    print(cfg)

    input_folder = os.path.normpath(cfg['input_dir'])
    output_folder = os.path.normpath(cfg['output_dir'])

    # Find QS1 generated files from output_folder
    tests_root = os.path.dirname(os.path.dirname(os.path.dirname(output_folder)))
    qs1_generated = os.path.join(tests_root, 'qs1_files', 'Data', 'generated_files')
    # Must already have generated results from QS1 and not removed
    assert os.path.exists(qs1_generated)

    # This copies all data from QS1
    copy_qs1_generated(qs1_generated, output_folder)

    print("input_folder exists? {}".format(os.path.exists(input_folder)))
    print("output_folder exists? {}".format(os.path.exists(output_folder)))

    print(os.listdir(output_folder))

    # After copying from QS1, run RS2
    returncode = call_rs2_bat()
    assert returncode == 0

    # Assess results
    assert os.path.exists(os.path.join(output_folder, 'tableau_input_file_QS1.xlsx'))

    tableau_file = pd.read_excel(os.path.join(output_folder, 'tableau_input_file_QS1.xlsx'),
                                 sheet_name='Scenarios', engine="openpyxl")

    # Should have 60 rows
    assert tableau_file.shape[0] == 60

    # After expanding scenario space, now have additional Projects
    proj_name_list = list(set(tableau_file.ProjectName))
    proj_name_list.sort()
    assert proj_name_list == ['L2-7 Complete Mitigation',
                              'L20-21 Complete Mitigation',
                              'L8-9 Complete Mitigation',
                              'L8-9 Partial Mitigation',
                              'No Vulnerability Projects']

    # Top ranked by net benefits is L2-7, check the recovery path and net benefits
    tableau_file.sort_values(by = ['NetBenefits_Discounted'],
                             ascending = [False], inplace = True)

    tableau_file = tableau_file.reset_index().copy()

    # assert tableau_file.ResiliencyProject[0] == 'L2-7'
    # assert tableau_file.Exposurerecoverypath[0] == '3,3,3,3,3,3,3,3,2,2,1,1'

    # Average net benefits
    avg_net_benef = tableau_file.groupby('ResiliencyProject')['NetBenefits_Discounted'].mean().sort_values(ascending = False)
    assert avg_net_benef.iloc[0] > 10000000
