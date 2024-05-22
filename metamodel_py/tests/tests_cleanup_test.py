# Cleanup of scenario output folders on completion of the tests
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/tests_cleanup_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import shutil

def test_teardown_scenario_outputs():

    # For all tests except RS3
    test_file_locations = ['qs1_files',
                           'qs2_files/Example_A',
                           'qs2_files/Example_B',
                           'qs2_files/Example_C',
                           'rs2_files',
                           'rs3_files',
                           'rs4_files']
    test_dir = os.path.dirname(os.path.realpath(__file__))

    output_dirs = []
    for f in test_file_locations:
        output_dirs.append(os.path.join(test_dir, f, 'Data', 'generated_files'))

    for d in output_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)

    assert not os.path.exists(output_dirs[0])
    assert not os.path.exists(output_dirs[1])
    assert not os.path.exists(output_dirs[2])
    assert not os.path.exists(output_dirs[3])
    assert not os.path.exists(output_dirs[4])
    assert not os.path.exists(output_dirs[5])
    assert not os.path.exists(output_dirs[6])
