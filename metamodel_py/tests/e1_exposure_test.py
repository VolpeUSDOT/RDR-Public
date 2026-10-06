# Functional test of Reference Scenario 7 - Exposure Analysis Tool
# Run RDR Reference Scenario 7, evaluate outputs are as expected
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/e1_exposure_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import re
import shutil
import pandas as pd
import sys
from pathlib import Path

test_file_location = 'e1_files'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def call_e1_bat():
    bat_file = 'run_exposure_e1test.bat'
    returncode = subprocess.call(os.path.join(file_dir_path, bat_file))
    return returncode

def test_e1():
    print("running test e1")
    returncode = call_e1_bat()
    assert returncode == 0

    relative_path = Path(__file__).resolve().parent

    # check output exists
    output_1 = relative_path / "e1_files" / "Data" / "generated_files" / "haz1.csv"
    output_2 = relative_path / "e1_files" / "Data" / "generated_files" / "haz2.csv"
    #assert output_1.exists()
    #assert output_2.exists()

    # check link_availability
    df = pd.read_csv(output_1)
    assert round(df["link_availability"].sum(), 2) == 62.98

    df = pd.read_csv(output_2)
    assert round(df["link_availability"].sum(), 2) == 66.41

    copy_output_1 = relative_path / "qs1_files" / "Data" / "inputs" / "Hazards" / "haz1.csv"
    copy_output_2 = relative_path / "qs1_files" / "Data" / "inputs" / "Hazards" / "haz2.csv"
    shutil.copy(str(output_1), str(copy_output_1))
    shutil.copy(str(output_2), str(copy_output_2))
    