#!/usr/bin/env python
# coding: utf-8


# ---------------------------------------------------------------------------------------------------
# Name: rdr_Metamodel
#
# Fits metamodel regressions for the set of completed AequilibraE runs.
#
# ---------------------------------------------------------------------------------------------------
import os
import shutil
import subprocess
from rdr_supporting import log_subprocess_output, log_subprocess_error


def main(input_folder, output_folder, cfg, logger):
    logger.info("Start: regression module")

    """
    Execute rdr_Metamodel_Regression.Rmd, which conducts the metamodel regressions for the set of completed
    AequilibraE runs.

    This method calls an R script, rdr_Regression_Report_Compile.R, which renders an RMarkdown file,
    rdr_Metamodel_Regression.Rmd. The end results are
    1. A stand-alone HTML file with the completed regression results
    2. A csv file of the complete regression results, stored in the generated_files directory
    """

    # validate that rdr_Regression_Report_Compile.R is present in the current directory
    if not os.path.exists('rdr_Regression_Report_Compile.R'):
        logger.error(("R CODE FILE ERROR: rdr_Regression_Report_Compile.R " +
                      "could not be found in directory {}".format(os.getcwd())))
        raise Exception(("R CODE FILE ERROR: rdr_Regression_Report_Compile.R " +
                         "could not be found in directory {}".format(os.getcwd())))

    # validate that Rscript.exe is callable
    if shutil.which('Rscript.exe') is None:
        logger.error("R EXECUTABLE ERROR: Rscript.exe could not be found")
        raise Exception("R EXECUTABLE ERROR: Rscript.exe could not be found")

    R_process = subprocess.Popen(['Rscript.exe', 'rdr_Regression_Report_Compile.R', input_folder, output_folder,
                                 cfg['run_id'], cfg['metamodel_type']],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    log_subprocess_output(R_process.stdout, logger)
    is_error = log_subprocess_error(R_process.stderr, logger)
    if is_error:
        logger.error("METAMODEL R CODE ERROR: rdr_Regression_Report_Compile.R encountered an error")
        raise Exception("METAMODEL R CODE ERROR: rdr_Regression_Report_Compile.R encountered an error")

    # move rendered HTML file when complete to the output folder, will replace any existing file
    if not os.path.exists('rdr_Metamodel_Regression.html'):
        logger.error("METAMODEL OUTPUT FILE ERROR: rdr_Metamodel_Regression.html could not be found")
        raise Exception("METAMODEL OUTPUT FILE ERROR: rdr_Metamodel_Regression.html could not be found")
    shutil.move('rdr_Metamodel_Regression.html', os.path.join(output_folder, 'rdr_Metamodel_Regression_' +
                                                              str(cfg['run_id']) + '.html'))

    logger.info("Finished: regression module")
