# Functional test of Reference Scenario 5 - Format Network Helper Tools
# Run RDR Reference Scenario 5, evaluate outputs are as expected
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/rs5_networkprep_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import re
import shutil
import pandas as pd
import sys
from pathlib import Path

test_file_location = 'rs5_files'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def call_rs5_bat():
    bat_file = 'run_network_rs5test.bat'
    returncode = subprocess.call(os.path.join(file_dir_path, bat_file))
    return returncode

def test_rs5():
    print("running test rs5")
    returncode = call_rs5_bat()
    assert returncode == 0

    relative_path = Path(__file__).resolve().parent

    # check output exists
    output_1 = relative_path / "rs5_files" / "Data" / "generated_files" / "gtfs_gis.gpkg"
    output_2 = relative_path / "rs5_files" / "Data" / "generated_files" / "RDR_Transit_Overlay.gpkg"
    output_3 = relative_path / "rs5_files" / "Data" / "generated_files" / "combined_link.csv"

    # check combined link CSV
    df = pd.read_csv(output_3)
    assert len(df) == 48

    assert output_1.exists() is True
    assert output_2.exists() is True
    