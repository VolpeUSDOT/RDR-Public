#!/usr/bin/env python
# coding: utf-8

# Base Run of AequilibraE
#
# Inputs: demand, non-disrupted networks
#
# Outputs: shortest path skims (matrices\sp_base.omx), routing results (matrices\rt_base.omx)

from os.path import join, exists
from aequilibrae import Parameters
from aequilibrae.project import Project
from aequilibrae.paths import NetworkSkimming
from aequilibrae.matrix import AequilibraeMatrix
# from aequilibrae import logger  # TODO: make decision on if to incorporate AequilibraE logger
from aequilibrae.paths import TrafficAssignment, TrafficClass


def run_aeq_base(run_params, run_folder, cfg, logger):
    fldr = run_folder
    mtx_fldr = 'matrices'

    project = Project()
    project.open(fldr)
    proj_name = 'project_database.sqlite'  # the network comes from this sqlite database
    if not exists(join(fldr, proj_name)):
        logger.error("SQLITE DATABASE ERROR: {} could not be found".format(join(fldr, proj_name)))
        raise Exception("SQLITE DATABASE ERROR: {} could not be found".format(join(fldr, proj_name)))

    p = Parameters()
    p.parameters['system']['logging_directory'] = fldr
    p.write_back()

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

    # We build all graphs
    project.network.build_graphs()
    # We get warnings that several fields in the project are filled with NaNs. Which is true, but we won't
    # use those fields

    # We grab the graph for cars
    graph = project.network.graphs['c']

    # Let's say we want to minimize travel time
    graph.set_graph('free_flow_time')

    # And will skim time and distance while we are at it
    graph.set_skimming(['free_flow_time', 'distance'])

    # And we will allow paths to be computed going through other centroids/centroid connectors as specified by user
    # Should be set to False for the Sioux Falls Quick Start network, as all nodes are centroids
    logger.debug("blocked_centroid_flows parameter set to {}".format(cfg['blocked_centroid_flows']))
    graph.set_blocked_centroid_flows(cfg['blocked_centroid_flows'])

    # look at the matrices - not essential to workflow
    proj_matrices = project.matrices
    proj_matrices.list()

    # SKIMMING
    # ----------------------------------------------------------------

    # And run the skimming
    skm = NetworkSkimming(graph)
    skm.execute()

    # The result is an AequilibraEMatrix object
    skims = skm.results.skims

    # Which we can manipulate directly from its temp file, if we wish
    skims.matrices

    # We can save it to the project if we want
    # skm.save_to_project('base_skims')  # TODO: figure out how to save/overwrite to database

    # We can export to OMX
    skims.export(join(fldr, mtx_fldr, 'sp_' + scenname + '.omx'))  # changes for each run

    # TRAFFIC ASSIGNMENT WITH SKIMMING
    # ----------------------------------------------------------------

    demand = AequilibraeMatrix()
    demand.load(join(fldr, mtx_fldr, socio + '_demand_summed.omx'))
    # Either 'matrix' or 'nocar'
    demand.computational_view(['matrix'])  # We will only assign one user class stored as 'matrix' or 'nocar' inside the OMX file

    assig = TrafficAssignment()

    # Creates the assignment class
    # Currently restricted to 'car', can be made multimodal later
    assigclass = TrafficClass(name='car', graph=graph, matrix=demand)

    # The first thing to do is to add at list of traffic classes to be assigned
    assig.set_classes([assigclass])

    assig.set_vdf("BPR")  # This is not case-sensitive  # Then we set the volume delay function

    assig.set_vdf_parameters({"alpha": "alpha", "beta": "beta"})  # Get parameters from link file

    assig.set_capacity_field("capacity")  # The capacity and travel times as they exist in the graph
    assig.set_time_field("free_flow_time")

    # And the algorithm we want to use to assign
    assig.set_algorithm('bfw')
    # assig.set_algorithm('msa')  # All-or-nothing

    # config variable is in dollars per hour
    cent_per_min = (100.0/60.0)*cfg['vot_per_hour']
    assigclass.set_vot(cent_per_min)
    assigclass.set_fixed_cost("toll", 1.0)

    # Since I haven't checked the parameters file, let's make sure convergence criteria is good
    assig.max_iter = 100  # was 1000 or 100
    assig.rgap_target = 0.01  # was 0.00001 or 0.01

    assig.execute()  # We then execute the assignment

    # The link flows are easy to export
    # We do so for csv and AequilibraEData
    assigclass.results.save_to_disk(join(fldr, 'link_flow_' + scenname + '.csv'), output="loads")  # changes for each run

    # The skims are easy to get

    # The blended one are here
    avg_skims = assigclass.results.skims
    last_skims = assigclass._aon_results.skims   # New AE092, not used in this code
    # Export to OMX
    avg_skims.export(join(fldr, mtx_fldr, 'rt_' + scenname + '.omx'))

    # Optional AE7 reporting
    convergence_report = assig.report()
    convergence_report.head()

    volumes = assig.results()
    volumes.head()

    # We could export it to CSV or AequilibraE data, but let's put it directly into the results database
    # assig.save_results("base_year_assignment")  # TODO: figure out how to save/overwrite to database

    demand.close()
    project.close()
