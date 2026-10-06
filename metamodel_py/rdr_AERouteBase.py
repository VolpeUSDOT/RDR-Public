#!/usr/bin/env python
# coding: utf-8

# Base Run of AequilibraE
#
# Inputs: demand, non-disrupted networks
#
# Outputs: shortest path skims (matrices\sp_base.omx), routing results (matrices\rt_base.omx)

from os.path import join
# from aequilibrae import logger  # TODO: make decision on if to incorporate AequilibraE logger
from rdr_AERouteCore import build_car_graph, export_assignment_skims, open_project, run_bfw_assignment, \
    run_shortest_path_skimming, save_assignment_results


def run_aeq_base(run_params, run_folder, cfg, logger):
    """Run the base AequilibraE assignment and export skims and link flows.

    :param run_params: Parameters describing one AequilibraE run.
    :param run_folder: Run-specific AequilibraE working directory.
    :param cfg: Parsed configuration dictionary.
    :param logger: Logger used for status, warning, and error reporting.
    :returns: None. The function exports skims, link flows, and assignment outputs.
    :rtype: None
    :db_reads: AequilibraE reads `project_database.sqlite` through `Project.open()`.
    :db_writes: AequilibraE writes assignment results and skims back to `project_database.sqlite` and the run folders.
    """
    fldr = run_folder
    mtx_fldr = 'matrices'

    project = open_project(fldr, logger)

    # Because assignment takes a long time, we want the log to be shown here
    # TODO: refine this code block
    # import logging
    # stdout_handler = logging.StreamHandler(sys.stdout)
    # formatter = logging.Formatter("%(asctime)s;%(name)s;%(levelname)s ; %(message)s")
    # stdout_handler.setFormatter(formatter)
    # logger.addHandler(stdout_handler)

    # project.load(join(fldr, proj_name))  # Not needed because we did a project.open  SBS 3/2/22
    socio = run_params['socio']
    projgroup = run_params['projgroup']
    scenname = socio + projgroup
    logger.debug("running shortest path skim for {}".format(scenname))

    graph = build_car_graph(project, cfg, logger)

    # SKIMMING
    # ----------------------------------------------------------------

    run_shortest_path_skimming(graph, join(fldr, mtx_fldr, 'sp_' + scenname + '.omx'))  # changes for each run

    # TRAFFIC ASSIGNMENT WITH SKIMMING
    # ----------------------------------------------------------------

    demand, assig, assigclass = run_bfw_assignment(
        graph,
        join(fldr, mtx_fldr, socio + '_demand_summed.omx'),
        run_params['matrix_name'],
        cfg,
        force_float_demand=True)

    # The link flows are easy to export. This code is compatible with AequilibraE 1.4.2
    # We do so for csv and AequilibraEData
    save_assignment_results(assig, join('link_flow', scenname), join(fldr, 'link_flow_' + scenname + '.csv'))
    # assigclass.results.save_to_disk(join(fldr, 'link_flow_' + scenname + '.csv'), output="loads")  # changes for each run. Per AequilibraE 1.1.4, this code is deprecated

    # The skims are easy to get

    # The blended one are here
    avg_skims = export_assignment_skims(assigclass, join(fldr, mtx_fldr, 'rt_' + scenname + '.omx'))
    last_skims = assigclass._aon_results.skims   # New AE092, not used in this code

    # Optional AE7 reporting
    convergence_report = assig.report()
    convergence_report.head()

    volumes = assig.results()
    volumes.head()

    # We could export it to CSV or AequilibraE data, but let's put it directly into the results database
    # assig.save_results("base_run_assignment")  # TODO: figure out how to save/overwrite to database

    demand.close()
    project.close()
