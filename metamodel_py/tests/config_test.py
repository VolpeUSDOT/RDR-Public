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
import shutil

test_file_location = 'qs1_files'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def teardown_readconfig(output_folder):
    """Remove the generated output folder from the config test.

    :param output_folder: Output directory for generated files.
    :returns: None. The function removes the generated output folder.
    :rtype: None
    """
    shutil.rmtree(output_folder)

def test_files_exists():
    """Verify that the QS1 config and fixture files exist.

    :returns: None. The assertions fail if the fixtures are missing.
    :rtype: None
    """
    assert os.path.isfile(os.path.join(file_dir_path, 'QS1.config'))
    assert os.path.isfile(os.path.join(file_dir_path, 'Data/inputs/Model_Parameters.xlsx'))
    assert os.path.isfile(os.path.join(file_dir_path, 'Data/inputs/LookupTables/project_info.csv'))

def test_conf():
    """Verify that the QS1 config file parses correctly.

    :returns: None. The assertions fail if the config parser misbehaves.
    :rtype: None
    """
    import rdr_setup
    import rdr_supporting
    path_to_config = os.path.join(file_dir_path, 'QS1.config')
    error_list, cfg = rdr_setup.read_config_file(path_to_config, 'config')

    input_folder = cfg['input_dir']
    output_folder = cfg['output_dir']
    template_folder = cfg['template_dir']

    seed = cfg['seed']

    assert len(error_list) == 0
    assert os.path.isdir(input_folder)
    assert os.path.isdir(output_folder)
    assert os.path.isdir(template_folder)
    assert seed == '8888'

    teardown_readconfig(output_folder)
