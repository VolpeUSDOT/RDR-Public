#!/usr/bin/env python
# coding: utf-8

from os.path import join, exists

from aequilibrae import Parameters
from aequilibrae.project import Project
from aequilibrae.paths import NetworkSkimming
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import TrafficAssignment, TrafficClass


def open_project(fldr, logger):
    project = Project()
    project.open(fldr)
    proj_name = 'project_database.sqlite'  # the network comes from this sqlite database
    if not exists(join(fldr, proj_name)):
        logger.error("SQLITE DATABASE ERROR: {} could not be found".format(join(fldr, proj_name)))
        raise Exception("SQLITE DATABASE ERROR: {} could not be found".format(join(fldr, proj_name)))

    p = Parameters()
    p.parameters['system']['logging_directory'] = fldr
    p.write_back()

    return project


def build_car_graph(project, cfg, logger):
    # We build all graphs
    project.network.build_graphs(modes = ['c'])
    # Warnings that several fields in the project are filled with NaNs
    # can be ignored, files are not used

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

    return graph


def run_shortest_path_skimming(graph, output_path):
    # And run the skimming
    skm = NetworkSkimming(graph)
    skm.execute()

    # The result is an AequilibraEMatrix object
    skims = skm.results.skims

    # Which we can manipulate directly from its temp file, if we wish
    skims.matrices

    # We can export to OMX
    skims.export(output_path)

    return skm


def run_bfw_assignment(graph, demand_path, demand_matrix_name, cfg, force_float_demand=False):
    demand = AequilibraeMatrix()
    demand.load(demand_path)
    demand.computational_view([demand_matrix_name])

    assig = TrafficAssignment()

    # Setting demand to float here because if it is integer it fails downstream
    if force_float_demand:
        demand.matrix_view.dtype = float

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

    # config variable is in dollars per hour
    cent_per_min = (100.0/60.0)*cfg['vot_per_hour']
    assigclass.set_vot(cent_per_min)
    assigclass.set_fixed_cost("toll", 1.0)

    # Set the convergence criteria
    assig.max_iter = cfg['aeq_max_iter']  # default is 100
    assig.rgap_target = cfg['aeq_rgap_target']  # default is 0.01

    assig.execute()  # We then execute the assignment

    return demand, assig, assigclass


def save_assignment_results(assig, result_name, csv_path):
    assig.save_results(result_name)
    results_df = assig.results()
    results_df.to_csv(csv_path)
    return results_df


def export_assignment_skims(assigclass, output_path):
    avg_skims = assigclass.results.skims
    avg_skims.export(output_path)
    return avg_skims
