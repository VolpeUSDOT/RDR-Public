# We will use tests of the functions defined in each module in metamodel_py
# Will require uploading example data to the testing framework, caching (to save time), and testing each step.
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/config_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import sys
import re
import shutil

test_file_location = 'qs1_files'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def teardown_readconfig(output_folder):
    shutil.rmtree(output_folder)

def test_files_exists():
    assert os.path.isfile(os.path.join(file_dir_path, 'QS1.config'))
    assert os.path.isfile(os.path.join(file_dir_path, 'Data/inputs/UserInputs.xlsx'))
    assert os.path.isfile(os.path.join(file_dir_path, 'Data/inputs/LookupTables/project_info.csv'))

def test_conf():
    import rdr_setup
    import rdr_supporting
    path_to_config = os.path.join(file_dir_path, 'QS1.config')
    cfg = rdr_setup.read_config_file(path_to_config)

    input_folder = cfg['input_dir']
    output_folder = cfg['output_dir']

    seed = cfg['seed']

    assert os.path.isdir(input_folder)
    assert os.path.isdir(output_folder)
    assert seed == '8888'

    teardown_readconfig(output_folder)
