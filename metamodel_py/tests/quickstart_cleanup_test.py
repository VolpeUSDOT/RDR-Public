# Cleanup of QS output folders on completion of the tests
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/quickstart_cleanup_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import shutil

def test_teardown_qs_outputs():

    test_file_locations = ['qs1_files',
                           'qs2_files/Example_A',
                           'qs2_files/Example_B',
                           'qs2_files/Example_C',
                           'qs3_files']
    test_dir = os.path.dirname(os.path.realpath(__file__))

    output_dirs = []
    for f in test_file_locations:
        output_dirs.append(os.path.join(test_dir, f, 'Data', 'generated_files'))

    for d in output_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)

    print(output_dirs[0])

    assert not os.path.exists(output_dirs[0])
    assert not os.path.exists(output_dirs[1])
    assert not os.path.exists(output_dirs[2])
    assert not os.path.exists(output_dirs[3])
    assert not os.path.exists(output_dirs[4])
