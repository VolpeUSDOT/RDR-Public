# Functional test of Reference Scenario 3 - TAZ metrics

# Run RDR Reference Scenario 3, evaluate outputs are as expected
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/rs3_taz_metrics_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import subprocess
import re
import shutil
import pandas as pd
import sys

test_file_location = 'rs3_files'

file_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    test_file_location
    )

def call_rs3_bat():
    is_local = list(filter(lambda x: re.match('^C', x), os.path.abspath(__file__)))

    if 'C' in is_local:
        bat_file = 'run_TAZ_metrics_rs3test.bat'
    else:
        bat_file = 'run_TAZ_metrics_rs3test_gh.bat'

    returncode = subprocess.call(os.path.join(file_dir_path, bat_file))
    return returncode

def test_rs3():

    # Find output_folder
    import rdr_setup
    import rdr_supporting

    # Run RS3
    returncode = call_rs3_bat()
    assert returncode == 0

    # TODO: may not be needed after running RS3
    sys.path.insert(0, './helper_tools/benefits_analysis/')
    import equity_config_reader

    # Change working directory to RDR/helper_tools/benefits_analysis
    os.chdir(os.path.join(os.getcwd(), 'helper_tools', 'benefits_analysis'))

    path_to_config = os.path.join(file_dir_path, 'RS3_TAZ_metrics.config')
    equity_cfg = equity_config_reader.read_equity_config_file(path_to_config)

    print(equity_cfg)

    benefits_analysis_dir = os.path.normpath(equity_cfg['benefits_analysis_dir'])

    print("benefits_analysis_dir exists? {}".format(os.path.exists(benefits_analysis_dir)))

    print(os.listdir(benefits_analysis_dir))
    print(os.getcwd())

    # Get input_dir from the RDR config file
    rdr_cfg_path = equity_cfg['path_to_RDR_config_file']

    error_list, cfg = rdr_setup.read_config_file(rdr_cfg_path, 'config')
    assert len(error_list) == 0

    print(cfg)

    # The helper tool requires AequilibraE inputs from the main RDR input directory input_dir
    # Logs and the equity analysis core model outputs are stored in the equity output directory output_dir
    input_dir = cfg['input_dir']

    # # Tests:
    # # - nrow of TAZ by origin and destination; should be identical to input CEJST_TAZ_Mapping.csv
    # # - match the p-value of the proportion of trips disrupted with expected Number
    # # The p-value resulting from the chi square test was 0.97196, which is greater than the user-supplied p-value of 0.05.
    # # trips_percent_change_noresil
    # #-23.15032486
    # #-31.8499763
    assert os.path.exists(os.path.join(input_dir, 'CEJST_TAZ_Mapping.csv'))
    mapping_file = pd.read_csv(os.path.join(input_dir, 'CEJST_TAZ_Mapping.csv'))

    # assert os.path.exists(os.path.join(benefits_analysis_dir, 'MetricsByTAZ_RS3BenefitsAnalysis.html'))
    # tazorigin_file = pd.read_csv(os.path.join(benefits_analysis_dir, 'MetricsByTAZ_summary_RS3BenefitsAnalysis_byTAZofOrigin.csv'))
    # assert tazorigin_file.shape[0] == mapping_file.shape[0]

    # assert os.path.exists(os.path.join(benefits_analysis_dir, 'MetricsByTAZ_summary_RS3BenefitsAnalysis_byTAZofDestination.csv'))
    # tazdest_file = pd.read_csv(os.path.join(benefits_analysis_dir, 'MetricsByTAZ_summary_RS3BenefitsAnalysis_byTAZofDestination.csv'))
    # assert tazdest_file.shape[0] == mapping_file.shape[0]

    # assert os.path.exists(os.path.join(benefits_analysis_dir, 'MetricsByTAZ_summary_RS3BenefitsAnalysis_byTAZCategory.csv'))
    # trips_percent_change_noresil_vals = [-23.1074, -31.6498]
    # tazcat_file = pd.read_csv(os.path.join(benefits_analysis_dir, 'MetricsByTAZ_summary_RS3BenefitsAnalysis_byTAZCategory.csv'))

    # assert list(round(tazcat_file.trips_percent_change_noresil, 4)) == trips_percent_change_noresil_vals

    # # p-value test
    # report_file_path = os.path.join(benefits_analysis_dir, 'MetricsByTAZ_RS3BenefitsAnalysis.html')
    # with open(report_file_path, 'r', encoding="utf8") as file:
    #     report_file = file.read()

    # pval_value = 0.97104

    # regex = re.compile('(The p-value resulting from the chi square test was )(\\d{1}.\\d{0,10})+')

    # match = re.search(regex, report_file)

    # pval = match.group(2)

    # assert round(float(pval), 4) == round(pval_value, 4)
