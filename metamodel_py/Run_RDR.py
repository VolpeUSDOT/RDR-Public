#!/usr/bin/env python
# coding: utf-8


# ---------------------------------------------------------------------------------------------------
# Name: Run_RDR.py
#
# Purpose: This module automates aspects of the RDR Tool Suite, initiating steps specified by user supplied arguments.
#
# ---------------------------------------------------------------------------------------------------
import sys
import os
import logging
import datetime
import argparse
import traceback
import rdr_setup
import rdr_supporting

VERSION_NUMBER = "2023.2"
VERSION_DATE = "11/15/2023"

# ===================================================================================================
# set up config file and logger
# identify aeq runs needed
# execute set of aeq runs
# 1. set up input files for aeq run
# 2. execute single aeq run
# fit regression
# build recovery process analysis
# calculate return on investment analysis
# summarize output and clean up


def main():

    start_time = datetime.datetime.now()

    # PARSE ARGS
    # ----------------------------------------------------------------------------------------------

    program_description = 'Resilience Disaster Recovery Tool Suite. Version Number: ' \
                          + VERSION_NUMBER + ", (" + VERSION_DATE + ")"

    help_text = """
    The command-line input expected for this script is as follows:

    TheFilePathOfThisScript ConfigFilePath TaskToRun

    Valid values of TaskToRun include:


            # Setup
            # ---------------------------------------
            lhs: select runs to conduct in AequilibraE that will parameterize regression model (Latin hypercube method)
            -generate scenario space as cross product of regression model parameters to scope full set of possible runs
            aeq_run: calculate shortest path and routing results for all runs specified by lhs task
            -prepare input files for AequilibraE run given run parameters
            -load base network for AequilibraE
            -calc_link_availability method determines disruption on each link
            -create_network_link_csv method creates disrupted network file for AequilibraE
            -load disrupted network for AequilibraE
            aeq_compile: compile core model results across all runs

            # Regression
            # ---------------------------------------
            rr: create regression model based on AequilibraE results

            # ROI Analysis
            # ---------------------------------------
            recov_init: read in data for recovery process and calculate damage and repair for uncertainty scenarios
            recov_calc: consolidate metrics for economic analysis and interpolate results across period of analysis

            # Clean-up
            # ---------------------------------------
            o: summarize and write output report

            # Tools and Advanced Options
            # ---------------------------------------
            test: a test method that can be used for development and debugging
    """

    parser = argparse.ArgumentParser(description=program_description, usage=help_text)

    parser.add_argument("config_file", help="The full path to the XML Scenario", type=str)

    parser.add_argument("task", choices=("lhs", "aeq_run", "aeq_compile", "rr",
                                         "recov_init", "recov_calc", "o", "test"), type=str)

    if len(sys.argv) == 3:
        args = parser.parse_args()
    else:
        parser.print_help()
        sys.exit()

    # set up config
    # ----------------------------------------------------------------------------------------------
    if not os.path.exists(args.config_file):
        print('ERROR: config file {} can''t be found!'.format(args.config_file))
        sys.exit()

    cfg = rdr_setup.read_config_file(args.config_file)

    # set up file directories
    # ----------------------------------------------------------------------------------------------
    input_folder = cfg['input_dir']
    output_folder = cfg['output_dir']
    print("Input folder: {}".format(input_folder))
    print("Output folder: {}".format(output_folder))
    print("Run ID: {}".format(cfg['run_id']))

    # set up logging and report run start time
    # ----------------------------------------------------------------------------------------------
    logger = rdr_supporting.create_loggers(output_folder, args.task, cfg)

    logger.info("=========================================================================")
    logger.info("============== RDR RUN STARTING.  Run Option = {} ====================".format(str(args.task).upper()))
    logger.info("=========================================================================")

    # check output of ROI analysis check and log error/exit as needed
    from rdr_RecoveryAnalysis import check_roi_required_inputs
    is_covered = check_roi_required_inputs(input_folder, cfg, logger)
    if is_covered == 0:
        logger.error(("INCORRECT DATA FOR ROI ANALYSIS ERROR: incorrect input file data for " +
                      "ROI analysis type {} specified".format(cfg['roi_analysis_type'])))
        raise Exception(("INCORRECT DATA FOR ROI ANALYSIS ERROR: incorrect input file data for " +
                         "ROI analysis type {} specified, check log files for error".format(cfg['roi_analysis_type'])))

    # run the task
    # ----------------------------------------------------------------------------------------------
    try:

        if args.task in ['lhs']:
            # Define AequilibraE runs needed to fill in around TDM
            # Each run is defined by a unique set of run parameters
            from rdr_LHS import main
            logger.info("Calling the Latin hypercube sampling method")
            main(input_folder, output_folder, cfg, logger)

        elif args.task in ['aeq_run']:
            # Calculate shortest path and routing results for each run specified by 'lhs' task
            # Includes both preparation of input files and execution of AequilibraE run
            from rdr_RunAE import main
            logger.info("Running AequilibraE for runs chosen by the Latin hypercube sampling method")
            main(input_folder, output_folder, cfg, logger)

        elif args.task in ['aeq_compile']:
            # Compile results from multiple AequilibraE runs
            from rdr_CompileAE import main
            logger.info("Compiling AequilibraE runs")
            main(input_folder, output_folder, cfg, logger, False)

        elif args.task in ['rr']:
            # Build regression model from AequilibraE runs
            from rdr_Metamodel import main
            logger.info("Running metamodel")
            main(input_folder, output_folder, cfg, logger)
        
        # ---------------------------------------------------------------------------------------------------
        # None of the steps above should be re-run when conducting ROI analysis or generating visualizations,
        # only to create the metamodel in the first place
        # ---------------------------------------------------------------------------------------------------

        elif args.task in ['recov_init']:
            # Read in data from user input tables, exposure-damage tables, repair cost and time tables
            # Build out and extend uncertainty scenarios for hazard recovery and damage recovery
            from rdr_RecoveryInit import main
            logger.info("Building out scenario tables, constructing damage and recovery tables")
            main(input_folder, output_folder, cfg, logger)

        elif args.task in ['recov_calc']:
            # Consolidate outputs from regression and repair costs/times for ROI analysis
            from rdr_RecoveryAnalysis import main
            logger.info("Consolidating metamodel outputs, calculating economic analysis metrics")
            main(input_folder, output_folder, cfg, logger)

        elif args.task in ['o']:
            # Call generate_reports from rdr_supporting to consolidate logs into report
            # NOTE: generate_reports must be updated anytime a task is added
            logger.info("Creating output report")
            rdr_supporting.generate_reports(output_folder, cfg, logger)

        elif args.task in ['test']:
            # Test any method currently under development
            logger.info("Testing network prep module and validating AequilibraE results in 'test' task")
            run_params = {}
            run_params['socio'] = 'baseyear'  # examples: 'base', 'urban', 'suburban', 'water', 'baseyear'
            run_params['projgroup'] = '00'  # examples: strings like '00', '02'
            run_params['resil'] = 'no'  # examples: 'no', or strings like 'LXX-XX'
            run_params['elasticity'] = -1  # format: negative float or 0
            run_params['hazard'] = 'haz3'  # examples: strings containing storm surge + sea-level rise details
            run_params['recovery'] = '2'  # format: strings like X ft of exposure to subtract for recovery stage
            run_params['run_minieq'] = 1  # possibilities: 1 or 0
            run_params['matrix_name'] = 'matrix'  # possibilities: 'matrix' or 'nocar'
            from rdr_AESingleRun import run_AESingleRun
            run_AESingleRun(run_params, input_folder, output_folder, cfg, logger)

    except:
        stack_trace = traceback.format_exc()
        split_stack_trace = stack_trace.split('\n')
        print("!!!!!!!!!!!!!!!!!!!! EXCEPTION RAISED !!!!!!!!!!!!!!!!!!!!!!")
        for i in range(0, len(split_stack_trace)):
            trace_line = split_stack_trace[i].rstrip()
            if trace_line != "":
                print(trace_line)
        print("!!!!!!!!!!!!!!!!!!!! EXCEPTION RAISED !!!!!!!!!!!!!!!!!!!!!!")
        sys.exit(1)

    logger.info("======================== RDR RUN FINISHED.  {} ==================================".format(str(args.task).upper()))
    logger.info("======================== Total Runtime (HMS): \t{} \t ".format(rdr_supporting.get_total_runtime_string(start_time)))
    logger.info("=================================================================================")
    logger.runtime("{} Step - Total Runtime (HMS): \t{}".format(args.task, rdr_supporting.get_total_runtime_string(start_time)))
    logging.shutdown()


if __name__ == "__main__":
    main()
