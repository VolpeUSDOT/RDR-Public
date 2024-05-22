#!/usr/bin/env python
# coding: utf-8


# ---------------------------------------------------------------------------------------------------
# Name: rdr_suppporting
#
# Purpose: Contains support methods for logging and reporting.
#
# ---------------------------------------------------------------------------------------------------
import os
import logging
import datetime
import glob

from Run_RDR import VERSION_NUMBER


# ==============================================================================


def log_subprocess_output(pipe, logger):
    for line in iter(pipe.readline, b''):  # b'\n'-separated lines
        logger.info('R PROCESS: %r', line.strip().decode('ascii'))


# ==================================================================


def log_subprocess_error(pipe, logger):
    is_error = False

    for line in iter(pipe.readline, b''):  # b'\n'-separated lines
        if line != b'':
            is_error = True
        logger.error('R PROCESS: %r', line.strip().decode('ascii'))

    return is_error


# ==================================================================


# Taken from FTOT project, ftot_supporting.py
def get_total_runtime_string(start_time):
    end_time = datetime.datetime.now()

    duration = end_time - start_time

    seconds = duration.total_seconds()

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)

    hms = "{:02}:{:02}:{:02}".format(hours, minutes, seconds)

    return hms


# ==================================================================
# Note that this function is duplicated in rdr exposure grid overlay helper tool due to the
# different environment and slightly different logging setup required.
# Any updates here may also need to be applied to the helper tool version of the function.

# Taken from FTOT project, ftot_supporting.py
# <!--Create the logger -->
def create_loggers(dirLocation, task, cfg):
    """Create the logger"""

    loggingLocation = os.path.join(dirLocation, "logs")

    if not os.path.exists(loggingLocation):
        os.makedirs(loggingLocation)

    # BELOW ARE THE LOGGING LEVELS. WHATEVER YOU CHOOSE IN SETLEVEL WILL BE SHOWN ALONG WITH HIGHER LEVELS.
    # YOU CAN SET THIS FOR BOTH THE FILE LOG AND THE DOS WINDOW LOG
    # -----------------------------------------------------------------------------------------------------
    # CRITICAL       50
    # ERROR          40
    # WARNING        30
    # RESULT         25
    # INFO           20
    # CONFIG         19
    # RUNTIME        11
    # DEBUG          10
    # DETAILED_DEBUG  5

    logging.RESULT = 25
    logging.addLevelName(logging.RESULT, 'RESULT')

    logging.CONFIG = 19
    logging.addLevelName(logging.CONFIG, 'CONFIG')

    logging.RUNTIME = 11
    logging.addLevelName(logging.RUNTIME, 'RUNTIME')

    logging.DETAILED_DEBUG = 5
    logging.addLevelName(logging.DETAILED_DEBUG, 'DETAILED_DEBUG')

    logger = logging.getLogger('log')
    logger.setLevel(logging.DEBUG)

    logger.result = lambda msg, *args: logger._log(logging.RESULT, msg, args)
    logger.config = lambda msg, *args: logger._log(logging.CONFIG, msg, args)
    logger.runtime = lambda msg, *args: logger._log(logging.RUNTIME, msg, args)
    logger.detailed_debug = lambda msg, *args: logger._log(logging.DETAILED_DEBUG, msg, args)

    # FILE LOG
    # ------------------------------------------------------------------------------
    logFileName = task + "_log_" + cfg['run_id'] + "_" + datetime.datetime.now().strftime("%Y_%m_%d_%H-%M-%S") + ".log"
    file_log = logging.FileHandler(os.path.join(loggingLocation, logFileName), mode='a')
    file_log.setLevel(logging.DEBUG)

    file_log_format = logging.Formatter('%(asctime)s.%(msecs).03d %(levelname)-8s %(message)s',
                                        datefmt='%m-%d %H:%M:%S')
    file_log.setFormatter(file_log_format)

    # DOS WINDOW LOG
    # ------------------------------------------------------------------------------
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    # To show more detail on screen, i.e. for GitHub workflow, use DEBUG level
    # console.setLevel(logging.DEBUG)

    console_log_format = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', datefmt='%m-%d %H:%M:%S')
    console.setFormatter(console_log_format)

    # ADD THE HANDLERS
    # ----------------
    logger.addHandler(file_log)
    logger.addHandler(console)

    return logger


# ==================================================================


def generate_reports(dirLocation, cfg, logger):
    logger.info("start: parse log operation for reports")
    report_directory = os.path.join(dirLocation, "Reports")
    if not os.path.exists(report_directory):
        os.makedirs(report_directory)

    filetype_list = ['lhs', 'aeq_run', 'aeq_compile', 'rr', 'recov_init', 'recov_calc', 'o']
    # init the dictionary to hold them by type.  for the moment ignoring other types.
    log_file_dict = {}
    for x in filetype_list:
        log_file_dict[x] = []

    # get all of the log files matching the pattern
    log_files = glob.glob(os.path.join(dirLocation, "logs", "*_log_" + cfg['run_id'] + "_*_*_*_*-*-*.log"))

    # add log file name and date to dictionary
    # each entry in the array will be a tuple of (log_file_name, datetime object)

    for log_file in log_files:
        path_to, the_file_name = os.path.split(log_file)
        the_type = the_file_name.split("_log_" + cfg['run_id'] + "_", maxsplit=1)[0]
        the_date = datetime.datetime.strptime(the_file_name.split("_log_" + cfg['run_id'] + "_",
                                                                  maxsplit=1)[1].replace(".log", ""),
                                              "%Y_%m_%d_%H-%M-%S")

        if the_type in log_file_dict:
            log_file_dict[the_type].append((the_file_name, the_date))

    # sort each log type list by datetime so the most recent is first.
    for x in filetype_list:
        log_file_dict[x] = sorted(log_file_dict[x], key=lambda tup: tup[1], reverse=True)

    # create a list of log files to include in report by grabbing the latest version.
    # these will be in order by log type (i.e. lhs, aeq_run, etc)
    most_recent_log_file_set = []

    if len(log_file_dict['lhs']) > 0:
        most_recent_log_file_set.append(log_file_dict['lhs'][0])

    if len(log_file_dict['aeq_run']) > 0:
        most_recent_log_file_set.append(log_file_dict['aeq_run'][0])

    if len(log_file_dict['aeq_compile']) > 0:
        most_recent_log_file_set.append(log_file_dict['aeq_compile'][0])

    if len(log_file_dict['rr']) > 0:
        most_recent_log_file_set.append(log_file_dict['rr'][0])

    if len(log_file_dict['recov_init']) > 0:
        most_recent_log_file_set.append(log_file_dict['recov_init'][0])

    if len(log_file_dict['recov_calc']) > 0:
        most_recent_log_file_set.append(log_file_dict['recov_calc'][0])

    if len(log_file_dict['o']) > 0:
        most_recent_log_file_set.append(log_file_dict['o'][0])

    # figure out the last index of most_recent_log_file_set to include
    # by looking at dates.  if a subsequent step is seen to have an older
    # log than a preceding step, no subsequent logs will be used.
    # --------------------------------------------------------------------

    last_index_to_include = 0

    for i in range(1, len(most_recent_log_file_set)):
        # print most_recent_log_file_set[i]
        if i == 1:
            last_index_to_include += 1
        elif i > 1:
            if most_recent_log_file_set[i][1] > most_recent_log_file_set[i - 1][1]:
                last_index_to_include += 1
            else:
                break

    # print last_index_to_include
    # --------------------------------------------------------

    message_dict = {
        'RESULT': [],
        'CONFIG': [],
        'ERROR': [],
        'WARNING': [],
        'RUNTIME': []
    }

    for i in range(0, last_index_to_include + 1):

        in_file = os.path.join(dirLocation, "logs", most_recent_log_file_set[i][0])

        # task
        record_src = most_recent_log_file_set[i][0].split("_log_" + cfg['run_id'] + "_", maxsplit=1)[0].upper()

        with open(in_file, 'r') as rf:
            for line in rf:
                recs = line.strip()[19:].split(" ", maxsplit=1)
                if recs[0] in message_dict:
                    if len(recs) > 1:  # NOTE: exceptions at the end of the log will cause this to fail.
                        message_dict[recs[0]].append((record_src, recs[1].strip()))

    # dump to file
    # ---------------
    report_file_name = 'report_' + cfg['run_id'] + '_' + datetime.datetime.now().strftime("%Y_%m_%d_%H-%M-%S") + ".txt"

    report_file = os.path.join(report_directory, report_file_name)
    with open(report_file, 'w') as wf:

        wf.write('SCENARIO\n')
        wf.write('---------------------------------------------------------------------\n')
        wf.write('RDR Run ID\t:\t{}\n'.format(cfg['run_id']))
        wf.write('RDR Version\t:\t{}\n'.format(VERSION_NUMBER))

        wf.write('\nTOTAL RUNTIME\n')
        wf.write('---------------------------------------------------------------------\n')
        for x in message_dict['RUNTIME']:
            wf.write('{}\t:\t{}\n'.format(x[0], x[1]))

        wf.write('\nRESULTS\n')
        wf.write('---------------------------------------------------------------------\n')
        for x in message_dict['RESULT']:
            wf.write('{}\t:\t{}\n'.format(x[0], x[1]))

        wf.write('\nCONFIG\n')
        wf.write('---------------------------------------------------------------------\n')
        for x in message_dict['CONFIG']:
            wf.write('{}\t:\t{}\n'.format(x[0], x[1]))

        if len(message_dict['ERROR']) > 0:
            wf.write('\nERROR\n')
            wf.write('---------------------------------------------------------------------\n')
            for x in message_dict['ERROR']:
                wf.write('{}\t:\t\t{}\n'.format(x[0], x[1]))

        if len(message_dict['WARNING']) > 0:
            wf.write('\nWARNING\n')
            wf.write('---------------------------------------------------------------------\n')
            for x in message_dict['WARNING']:
                wf.write('{}\t:\t\t{}\n'.format(x[0], x[1]))

    logger.info("Done Parse Log Operation")
    logger.info("Report file location: {}".format(report_file))
