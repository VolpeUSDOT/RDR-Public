# Usage of automated tests

RDR uses automated testing to ensure the quality of the code base. The following tests are implemented currently:

1. `config_test.py`
2. `qs1_full_test.py`
3. `qs2A_test.py`
4. `qs2B_test.py`
5. `qs2C_test.py`
6. `rs2_test.py`
7. `rs3_taz_metrics_test.py`
8. `rs4_full_test.py`

The first validates that input folders are set up correctly, that the config file has the correct values, and that initial setup of the RDR run has been done.

The second runs Quick Start 1 from scratch, reads the compiled model results, and validates that the AequilibraE outputs match expected values.

The third - fifth are tests of (now deprecated) Quick Start 2, which modifies outputs of Quick Start 1. Therefore, QS1 has to be completed successfully first; the outputs in the `generated_files` directory of QS1 are copied over into the respective Data directories for each of the QS2 tests.
  + Example A runs a subset of the hazard scenarios
  + Example B changes parameters of the recovery module to analyze more hazard recovery cases
  + Example C changes how damage metrics are calculated in the economic analysis

The sixth runs Reference Scenario 2, which likewise modifies the outputs of QS1 by expanding the scenario space.

The seventh runs Reference Scenario 3, which is a test of the Benefits Analysis Tool using QS1 input files.

The eighth runs Reference Scenario 4, which includes a transit network and 0-car trip table.

A final 'test', `tests_cleanup_test.py`, removes all the `generated_files` directories from each test to ensure when running locally that a clean test is performed. When developing tests locally, remove this test file temporarily from the tests directory to keep generated outputs for debugging.

## Using the tests on GitHub

No user action is necessary to use these tests. Using GitHub Actions, a virtual machine is created on each push and pull request, formatted with a Windows operating system, and using Python 3.11. The necessary dependencies are installed for both Python and R from scratch, and the tests are run. The test suite takes about 10 minutes to run (about 7 minutes of which is the installation of dependencies).

## Using the tests locally

When developing new functionality, a developer can use these tests before pushing to GitHub as well.

The local test is done as follows. In your Anaconda Prompt (or other terminal):
```
conda activate RDRenv
cd C:/GitHub/RDR
pytest
```

Alternatively, specific test scripts can be run individually with this command:
```
python -m pytest metamodel_py/tests/qs1_full_test.py -v
```

Use pytest flag `-rP` for extra summary info for passed tests, `-rx` for failed tests.

## Developing new tests

Additional test coverage of RDR functionality will be developed to ensure the quality of each module. The basic setup is as follows:

- Any file ending in `*_test.py` in the `tests` directory will be run by the `pytest` module.
- A test file should be self-contained and carry out necessary steps to test a specific function.
- A test file will have functions to check to see if function outputs are as expected. The `pytest` module will run all functions beginning with `test` in the test file. For example, `config_test.py` has this test (only a portion shown):
```
def test_files_exists():
    assert os.path.isfile(os.path.join(file_dir_path, 'QS1.config'))
    ...
```

- A test file can rely on dependent steps to first generate some output and then evaluate the output matches expected values. For example, `qs1_full_test.py` includes these steps to first run a full RDR run from a `.bat` file and then assesses that the results match expected values.
```
def call_qs1_bat():
    subprocess.call(os.path.join(file_dir_path, 'run_rdr_full.bat'))

def test_qs1():
    # Run QS1
    call_qs1_bat()

    ...

    exp_max_trips = 360600.0

    assert obs_max_trips == exp_max_trips
```
