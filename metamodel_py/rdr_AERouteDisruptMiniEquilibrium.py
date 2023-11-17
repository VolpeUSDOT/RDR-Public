#!/usr/bin/env python
# coding: utf-8

# Disrupted Run of AequilibraE
#
# Inputs: demand, disrupted network, sp and rt skims from non-disrupted network (sp_base.omx, rt_base.omx)
#
# Outputs: adjusted demand, shortest path skims, routing results with disrupted network for road and transit metrics, comparison with non-disrupted
#
# Major steps
# 1. Set up AequilibraE environment
# 2. Obtain the shortest path skim from the disrupted network
# 3. Adjust the demand based on the shortest path skims from disrupted and base networks
# 4. Run routing on the new demand in the disrupted network
# 5. (Mini-equilibrium) Re-adjust the demand based on the congested skims, and run routing again
# 6. Generate summary statistics
#
# Filename conventions
# - socio, e.g., 'base'
# - projgroup, e.g., '04'
# - resil, e.g., 'no' or a project number
# - elasticity, e.g., -1.0 (elasname encoded as -10 x elasticity, e.g., 10)
# - hazard, e.g., '100yr3SLR' for 100 year flood with 3 feet sea level rise
# - recovery, e.g., '5' feet of recovery
#
# Base Scenario Name = socio + projgroup
#
# Scenario Name = basescenname + resil + elasname + hazard + recovery


from os.path import join, exists
import numpy as np
import pandas as pd
import openmatrix as omx
from aequilibrae import Parameters
from aequilibrae.project import Project
from aequilibrae.paths import NetworkSkimming
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import TrafficAssignment, TrafficClass

def run_aeq_disrupt_miniequilibrium(run_params, base_run_folder, disrupt_run_folder, cfg, logger):
    fldr = disrupt_run_folder
    mtx_fldr = 'matrices'
    largeval = 99999  # constant used as an upper bound for travel times in disruption analysis

    project = Project()
    project.open(fldr)
    proj_name = 'project_database.sqlite'  # the network comes from this sqlite database
    if not exists(join(fldr, proj_name)):
        logger.error("SQLITE DATABASE ERROR: {} could not be found".format(join(fldr, proj_name)))
        raise Exception("SQLITE DATABASE ERROR: {} could not be found".format(join(fldr, proj_name)))

    p = Parameters()
    p.parameters['system']['logging_directory'] = fldr
    p.write_back()

    socio = run_params['socio']
    projgroup = run_params['projgroup']
    resil = run_params['resil']
    elasticity = run_params['elasticity']
    elasname = str(int(10*-elasticity))
    hazard = run_params['hazard']
    recovery = run_params['recovery']
    basescenname = socio + projgroup
    scenname = basescenname + '_' + resil + '_' + elasname + '_' + hazard + '_' + recovery
    logger.debug("running shortest path skim for {}".format(scenname))

    # We build all graphs
    project.network.build_graphs()
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

    # SKIMMING
    # ----------------------------------------------------------------

    # And run the skimming
    skm = NetworkSkimming(graph)
    skm.execute()

    # The result is an AequilibraEMatrix object
    skims = skm.results.skims

    # Which we can manipulate directly from its temp file, if we wish
    skims.matrices

    # We can export to OMX
    skims.export(join(fldr, mtx_fldr, 'sp_disrupt_' + scenname + '.omx'))

    # Adjust demand
    #
    # If new travel time is very large, then new_demand = 0.
    #
    # If there is little difference between travel times (< 0.5 minutes), then new_demand = old_demand
    # (this also takes care of the case where both travel times are zero)
    #
    # Otherwise, the equation is new_demand = old_demand * (t_new / t_base) ^ elasticity,
    # where t_new is the new shortest-path travel time,
    # and t_base is the baseline (no disruption) shortest-path travel time

    # Input files
    infile = join(fldr, mtx_fldr, socio + '_demand_summed.omx')
    if not exists(infile):
        logger.error("DEMAND OMX FILE ERROR: {} could not be found".format(infile))
        raise Exception("DEMAND OMX FILE ERROR: {} could not be found".format(infile))
    baseskimfile = join(base_run_folder, mtx_fldr, 'sp_' + basescenname + '.omx')
    if not exists(baseskimfile):
        logger.error("BASE SKIMS FILE ERROR: {} could not be found".format(baseskimfile))
        raise Exception("BASE SKIMS FILE ERROR: {} could not be found".format(baseskimfile))
    disruptskimfile = join(fldr, mtx_fldr, 'sp_disrupt_' + scenname + '.omx')
    if not exists(disruptskimfile):
        logger.error("DISRUPT SKIMS FILE ERROR: {} could not be found".format(disruptskimfile))
        raise Exception("DISRUPT SKIMS FILE ERROR: {} could not be found".format(disruptskimfile))

    # Output file
    outfile = join(fldr, mtx_fldr, 'new_demand_summed.omx')

    # Read the input demand file
    f_input = omx.open_file(infile)
    # Either 'matrix' or 'nocar'
    m1 = f_input[run_params['matrix_name']]
    tazs = f_input.mapping('taz')
    logger.debug("Mappings: {}".format(f_input.list_mappings()))
    input_demand = np.array(m1)
    matrix_shape = f_input.shape()
    logger.debug("Shape: {}".format(matrix_shape))
    logger.debug("Number of tables: {}".format(len(f_input)))
    logger.debug("Table names: {}".format(f_input.list_matrices()))
    logger.debug("Attributes: {}".format(f_input.list_all_attributes()))
    logger.debug("Sum of trips: {}".format(np.sum(m1)))

    matrix_size = matrix_shape[0]
    if matrix_shape[0] != matrix_shape[1]:
        logger.error("Warning - OMX demand file is not a square matrix")
        raise Exception("AEQUILIBRAE RUN ERROR: input demand omx file is not a square matrix")

    # Set up the output demand array
    output_demand = np.zeros((matrix_size, matrix_size))
    f_output = omx.open_file(outfile, 'w')
    taz_list = list(tazs.keys())
    f_output.create_mapping('taz', taz_list)

    f_base = omx.open_file(baseskimfile)
    f_disrupt = omx.open_file(disruptskimfile)
    t_base = f_base['free_flow_time']
    t_disrupt = f_disrupt['free_flow_time']

    logger.debug("Base Skim Shape: {}".format(f_base.shape()))
    logger.debug("Number of tables: {}".format(len(f_base)))
    logger.debug("Table names: {}".format(f_base.list_matrices()))
    logger.debug("Attributes: {}".format(f_base.list_all_attributes()))
    logger.debug("New Skim Shape: {}".format(f_disrupt.shape()))
    logger.debug("Number of tables: {}".format(len(f_disrupt)))
    logger.debug("Table names: {}".format(f_disrupt.list_matrices()))
    logger.debug("Attributes: {}".format(f_disrupt.list_all_attributes()))

    trips_removed = 0.0
    trips_unchanged = 0.0
    trips_reduced = 0.0
    output_trips_reduced = 0.0
    # the IF statement gets replaced with a series of transformations to the output_demand matrix
    output_demand_df, (trips_removed, trips_unchanged, trips_reduced, output_trips_reduced) = get_output_demand(
        t_disrupt, t_base, input_demand, largeval, elasticity)
    output_demand = output_demand_df.to_numpy()

    logger.debug("removed: {};  unchanged: {};  reduced from {} to {}".format(trips_removed, trips_unchanged,
                                                                              trips_reduced, output_trips_reduced))
    circuitous_trips_removed = trips_reduced - output_trips_reduced

    f_output['matrix'] = output_demand
    f_output.close()
    f_input.close()
    f_base.close()
    f_disrupt.close()

    # Run routing on the new demand

    # TRAFFIC ASSIGNMENT WITH SKIMMING #
    # ----------------------------------------------------------------

    demand = AequilibraeMatrix()
    demand.load(join(fldr, mtx_fldr, 'new_demand_summed.omx'))
    demand.computational_view(['matrix'])  # We will only assign one user class stored as 'matrix' inside the OMX file

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
    assigclass.results.save_to_disk(join(fldr, 'link_flow_adjdem_' + scenname + '.csv'), output="loads")

    # The blended skims are here
    avg_skims = assigclass.results.skims

    # Export to OMX
    avg_skims.export(join(fldr, mtx_fldr, 'rt_disrupt_' + scenname + '.omx'))
    demand.close()

    # MINI-EQUILIBRIUM #
    # ----------------------------------------------------------------

    # Start of mini-equilibrium portion
    if run_params['run_minieq'] == 1:
        # Re-adjust demand and rerun routing
        #
        # We now use the congested travel times from the routing run, and reduce the elasticity by 50%
        # If new travel time is very large, then new_demand = 0
        #
        # If there is little difference between travel times (< 0.5 minutes), then new_demand = old_demand
        # (this also takes care of the case where both travel times are zero)
        #
        # Otherwise, the equation is new_demand = old_demand * (t_new / t_base) ^ (0.5 elasticity),
        # where t_new is the new routing (congested) travel time,
        # and t_base is the baseline (no disruption) shortest-path travel time
        #
        # Note: we might want to compare to the baseline (no disruption) routing (congested) travel time
        logger.debug("Starting mini-equilibrium portion of AequilibraE run")

        # Input files
        infile = join(fldr, mtx_fldr, socio + '_demand_summed.omx')
        baseskimfile = join(base_run_folder, mtx_fldr, 'rt_' + basescenname + '.omx')
        if not exists(baseskimfile):
            logger.error("BASE SKIMS FILE ERROR: {} could not be found".format(baseskimfile))
            raise Exception("BASE SKIMS FILE ERROR: {} could not be found".format(baseskimfile))
        disruptskimfile = join(fldr, mtx_fldr, 'rt_disrupt_' + scenname + '.omx')
        if not exists(disruptskimfile):
            logger.error("DISRUPT SKIMS FILE ERROR: {} could not be found".format(disruptskimfile))
            raise Exception("DISRUPT SKIMS FILE ERROR: {} could not be found".format(disruptskimfile))

        # Output file
        outfile = join(fldr, mtx_fldr, 'new_demand_summed.omx')

        # Read the input demand file
        f_input = omx.open_file(infile)
        # Either 'matrix' or 'nocar'
        m1 = f_input[run_params['matrix_name']]
        tazs = f_input.mapping('taz')
        logger.debug("Mappings: {}".format(f_input.list_mappings()))
        input_demand = np.array(m1)
        matrix_shape = f_input.shape()
        logger.debug("Shape: {}".format(matrix_shape))
        logger.debug("Number of tables: {}".format(len(f_input)))
        logger.debug("Table names: {}".format(f_input.list_matrices()))
        logger.debug("Attributes: {}".format(f_input.list_all_attributes()))
        logger.debug("Sum of trips: {}".format(np.sum(m1)))

        matrix_size = matrix_shape[0]
        if matrix_shape[0] != matrix_shape[1]:
            logger.warning("Warning - OMX demand file is not a square matrix")
            raise Exception("AEQUILIBRAE RUN ERROR: input demand omx file is not a square matrix")

        # Set up the output demand array
        output_demand = np.zeros((matrix_size, matrix_size))
        f_output = omx.open_file(outfile, 'w')
        taz_list = list(tazs.keys())
        f_output.create_mapping('taz', taz_list)

        f_base = omx.open_file(baseskimfile)
        f_disrupt = omx.open_file(disruptskimfile)
        t_base = f_base['free_flow_time']
        t_disrupt = f_disrupt['free_flow_time']
        logger.debug("Base Skim Shape: {}".format(f_base.shape()))
        logger.debug("Number of tables: {}".format(len(f_base)))
        logger.debug("Table names: {}".format(f_base.list_matrices()))
        logger.debug("Attributes: {}".format(f_base.list_all_attributes()))
        logger.debug("New Skim Shape: {}".format(f_disrupt.shape()))
        logger.debug("Number of tables: {}".format(len(f_disrupt)))
        logger.debug("Table names: {}".format(f_disrupt.list_matrices()))
        logger.debug("Attributes: {}".format(f_disrupt.list_all_attributes()))

        trips_removed = 0.0
        trips_unchanged = 0.0
        trips_reduced = 0.0
        output_trips_reduced = 0.0
        output_demand_df, (trips_removed, trips_unchanged, trips_reduced, output_trips_reduced) = get_output_demand(
            t_disrupt, t_base, input_demand, largeval, 0.5 * elasticity)
        output_demand = output_demand_df.to_numpy()

        logger.debug("removed: {};  unchanged: {};  reduced from {} to {}".format(trips_removed, trips_unchanged,
                                                                                  trips_reduced, output_trips_reduced))
        circuitous_trips_removed = trips_reduced - output_trips_reduced

        f_output['matrix'] = output_demand
        f_output.close()
        f_input.close()
        f_disrupt.close()
        f_base.close()

        # TRAFFIC ASSIGNMENT WITH SKIMMING #
        # ----------------------------------------------------------------

        demand = AequilibraeMatrix()
        demand.load(join(fldr, mtx_fldr, 'new_demand_summed.omx'))
        # We will only assign one user class stored as 'matrix' inside the OMX file
        demand.computational_view(['matrix'])

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
        assigclass.results.save_to_disk(join(fldr, 'link_flow_adjdem_' + scenname + '.csv'), output="loads")

        # The blended skims are here
        avg_skims = assigclass.results.skims

        # The ones for the last iteration are here
        last_skims = assigclass._aon_results.skims

        # Export to OMX 
        avg_skims.export(join(fldr, mtx_fldr, 'rt_disrupt_' + scenname + '.omx'))
        demand.close()

    # Calculate summary statistics

    f = omx.open_file(join(fldr, mtx_fldr, socio + '_demand_summed.omx'), 'r')
    logger.debug("DEMAND FILE Shape: {}   Tables: {}   Mappings: {}".format(f.shape(), f.list_matrices(),
                                                                            f.list_mappings()))
    # Either 'matrix' or 'nocar'
    dem = f[run_params['matrix_name']]

    nf = omx.open_file(join(fldr, mtx_fldr, 'new_demand_summed.omx'), 'r')
    logger.debug("DEMAND FILE Shape: {}   Tables: {}   Mappings: {}".format(nf.shape(), nf.list_matrices(),
                                                                            nf.list_mappings()))
    newdem = nf['matrix']

    spbf = omx.open_file(join(base_run_folder, mtx_fldr, 'sp_' + basescenname + '.omx'), 'r')
    logger.debug("SP BASE SKIM FILE Shape: {}   Tables: {}   Mappings: {}".format(spbf.shape(), spbf.list_matrices(),
                                                                                  spbf.list_mappings()))
    spbt = spbf['free_flow_time']
    spbd = spbf['distance']

    rtbf = omx.open_file(join(base_run_folder, mtx_fldr, 'rt_' + basescenname + '.omx'), 'r')
    logger.debug("RT BASE SKIM FILE Shape: {}   Tables: {}   Mappings: {}".format(rtbf.shape(), rtbf.list_matrices(),
                                                                                  rtbf.list_mappings()))
    rtbt = rtbf['free_flow_time']
    rtbd = rtbf['distance']

    df_spbt = pd.DataFrame(data=spbt)
    df_spbd = pd.DataFrame(data=spbd)
    df_rtbt = pd.DataFrame(data=rtbt)
    df_rtbd = pd.DataFrame(data=rtbd)
    df_dem = pd.DataFrame(data=dem)
    df_newdem = pd.DataFrame(data=newdem)

    # Summary information on the input trip tables
    logger.debug("Sum of demand trips: {:.9}".format(np.sum(dem)))
    logger.debug("Sum of new demand trips: {:.9}".format(np.sum(newdem)))

    # Assemble totals for base shortest path and base routing
    # Note: to improve efficiency, this could be done in rdr_AERouteBase,
    # but would need to save the totals somewhere and read them in this module

    spb_cumtripcount = 0.0
    spb_cumtime = 0.0
    spb_cumdist = 0.0

    # Shortest path base times and distances
    # matrix same size as spbt, true where each entry is <largeval, otherwise false
    bool_spbt = df_spbt < largeval
    # sums demand where spbt < largeval
    spb_cumtripcount = (df_dem.where(bool_spbt, other=0)).sum().sum()
    spb_cumtime = ((df_dem.where(bool_spbt, other=0))*df_spbt).sum().sum()
    spb_cumdist = ((df_dem.where(bool_spbt, other=0))*df_spbd).sum().sum()

    logger.debug("Base,SP,{},{:.8},{:.8},{:.8}".format(basescenname, spb_cumtripcount, spb_cumdist, spb_cumtime/60))

    rtb_cumtripcount = 0.0
    rtb_cumtime = 0.0
    rtb_cumdist = 0.0

    # Routing base times and distances
    bool_rtbt = df_rtbt < largeval
    rtb_cumtripcount = (df_dem.where(bool_rtbt, other=0)).sum().sum()
    rtb_cumtime = ((df_dem.where(bool_rtbt, other=0))*df_rtbt).sum().sum()
    rtb_cumdist = ((df_dem.where(bool_rtbt, other=0))*df_rtbd).sum().sum()

    logger.debug("Base,RT,{},{:.8},{:.8},{:.8}".format(basescenname, rtb_cumtripcount, rtb_cumdist, rtb_cumtime/60))

    # Open disruption skim files and assemble the totals
    spdf = omx.open_file(join(fldr, mtx_fldr, 'sp_disrupt_' + scenname + '.omx'), 'r')
    logger.debug("SP DISRUPT SKIM FILE Shape: {}   Tables: {}   Mappings: {}".format(spbf.shape(),
                                                                                          spbf.list_matrices(),
                                                                                          spbf.list_mappings()))
    spdt = spdf['free_flow_time']
    spdd = spdf['distance']

    rtdf = omx.open_file(join(fldr, mtx_fldr, 'rt_disrupt_' + scenname + '.omx'), 'r')
    logger.debug("RT DISRUPT SKIM FILE Shape: {}   Tables: {}   Mappings: {}".format(rtdf.shape(),
                                                                                          rtdf.list_matrices(),
                                                                                          rtdf.list_mappings()))
    rtdt = rtdf['free_flow_time']
    rtdd = rtdf['distance']

    df_spdt = pd.DataFrame(data=spdt)
    df_spdd = pd.DataFrame(data=spdd)
    df_rtdt = pd.DataFrame(data=rtdt)
    df_rtdd = pd.DataFrame(data=rtdd)

    spd_cumtripcount = 0.0
    spd_cumtime = 0.0
    spd_cumdist = 0.0
    spd_basecumtime = 0.0
    spd_basecumdist = 0.0

    # Shortest path disrupt times and distances
    spdt_bool = df_spdt < largeval
    spd_cumtripcount = (df_newdem.where(spdt_bool, other=0)).sum().sum()
    spd_cumtime = ((df_newdem.where(spdt_bool, other=0))*df_spdt).sum().sum()
    spd_cumdist = ((df_newdem.where(spdt_bool, other=0))*df_spdd).sum().sum()
    spd_basecumtime = ((df_newdem.where(spdt_bool, other=0))*df_spbt).sum().sum()
    spd_basecumdist = ((df_newdem.where(spdt_bool, other=0))*df_spbd).sum().sum()

    logger.debug("Disrupt,SP,{},{:.8},{:.8},{:.8},{:.8},{:.8},{:.8}".format(scenname, spd_cumtripcount, spd_cumdist,
                                                                            spd_cumtime/60, spd_basecumdist,
                                                                            spd_basecumtime/60,
                                                                            circuitous_trips_removed))

    rtd_cumtripcount = 0.0
    rtd_basecumtime = 0.0
    rtd_basecumdist = 0.0
    rtd_cumtime = 0.0
    rtd_cumdist = 0.0

    # Routing disrupt times and distances
    spdt_and_rtdt_bool = (df_spdt < largeval) & (df_rtdt < largeval)
    rtd_cumtripcount = (df_newdem.where(spdt_and_rtdt_bool, other=0)).sum().sum()
    rtd_cumtime = ((df_newdem.where(spdt_and_rtdt_bool, other=0))*df_rtdt).sum().sum()
    rtd_cumdist = ((df_newdem.where(spdt_and_rtdt_bool, other=0))*df_rtdd).sum().sum()
    rtd_basecumtime = ((df_newdem.where(spdt_and_rtdt_bool, other=0))*df_rtbt).sum().sum()
    rtd_basecumdist = ((df_newdem.where(spdt_and_rtdt_bool, other=0))*df_rtbd).sum().sum()

    logger.debug("Disrupt,RT,{},{:.8},{:.8},{:.8},{:.8},{:.8}".format(scenname, rtd_cumtripcount, rtd_cumdist,
                                                                      rtd_cumtime/60, rtd_basecumdist,
                                                                      rtd_basecumtime/60))

    # Calculate separate car and transit metrics
    if cfg['calc_transit_metrics']:
        logger.info("Calculating transit-specific metrics for scenario {}".format(scenname))
        # Read in network attributes file
        network_file = join(cfg['input_dir'], 'Networks', basescenname + '.csv')
        if not exists(network_file):
            logger.error("NETWORK FILE ERROR: {} could not be found".format(network_file))
            raise Exception("NETWORK FILE ERROR: {} could not be found".format(network_file))

        if run_params['matrix_name'] == 'matrix':
            network = pd.read_csv(network_file, usecols=['link_id', 'length', 'facility_type', 'toll', 'travel_time'],
                                  converters={'link_id': int, 'length': float, 'facility_type': str, 'toll': float, 'travel_time': float})
        elif run_params['matrix_name'] == 'nocar':
            network = pd.read_csv(network_file, usecols=['link_id', 'length', 'facility_type', 'toll_nocar', 'travel_time_nocar'],
                                  converters={'link_id': int, 'length': float, 'facility_type': str, 'toll_nocar': float, 'travel_time_nocar': float})
            network.rename({'toll_nocar': 'toll', 'travel_time_nocar': 'travel_time'}, axis='columns', inplace=True)
        else:
            logger.error("AEquilibraE disrupt run requires 'matrix' or 'nocar' for matrix_name variable in run_params.")
            raise Exception("Invalid option for variable matrix_name in run_params in AEquilibraE disrupt run.")

        # Read in link flows file
        link_flow_file = join(fldr, 'link_flow_adjdem_' + scenname + '.csv')
        if not exists(link_flow_file):
            logger.error("LINK FLOW FILE ERROR: {} could not be found".format(link_flow_file))
            raise Exception("LINK FLOW FILE ERROR: {} could not be found".format(link_flow_file))

        link_flows = pd.read_csv(link_flow_file, usecols=['index', 'matrix_tot'],
                                 converters={'index': int, 'matrix_tot': float})

        transit_calcs = pd.merge(network, link_flows, how='left', left_on='link_id', right_on='index', indicator=True)
        logger.debug(("Number of links not found in link flows " +
                      "table: {}".format(sum(transit_calcs['_merge'] == 'left_only'))))
        if sum(transit_calcs['_merge'] == 'left_only') == transit_calcs.shape[0]:
            logger.error(("TABLE JOIN ERROR: Join of network links file with link flows table " +
                         "failed to produce any matches for scenario {}. Check the corresponding table columns.".format(scenname)))
            raise Exception(("TABLE JOIN ERROR: Join of network links file with link flows table " +
                             "failed to produce any matches for scenario {}. Check the corresponding table columns.".format(scenname)))
        transit_calcs.drop(labels=['index', '_merge'], axis=1, inplace=True)
        transit_calcs['matrix_tot'] = np.where(transit_calcs['matrix_tot'].isna(), 0, transit_calcs['matrix_tot'])
        transit_calcs = transit_calcs.assign(miles_tot=transit_calcs['matrix_tot'] * transit_calcs['length'],
                                             hours_tot=transit_calcs['matrix_tot'] * transit_calcs['travel_time'] / 60)

        # Pull out transit and car metrics based on facility type
        # Calculate four light rail (lr) metrics, four heavy rail/subway (hr) metrics, four bus metrics, and three car metrics
        # Unlinked trip counts
        rtd_lrtrips = transit_calcs.loc[transit_calcs['facility_type'] == '600', 'matrix_tot'].sum().sum()
        rtd_hrtrips = transit_calcs.loc[transit_calcs['facility_type'].isin(['601', '602']), 'matrix_tot'].sum().sum()
        rtd_bustrips = transit_calcs.loc[transit_calcs['facility_type'] == '603', 'matrix_tot'].sum().sum()
        # Count on road centroid connectors then divide by 2
        rtd_cartrips = transit_calcs.loc[transit_calcs['facility_type'] == '901', 'matrix_tot'].sum().sum() / 2
        # Passenger miles traveled
        rtd_lrpmt = transit_calcs.loc[transit_calcs['facility_type'] == '100', 'miles_tot'].sum().sum()
        rtd_hrpmt = transit_calcs.loc[transit_calcs['facility_type'].isin(['101', '102']), 'miles_tot'].sum().sum()
        rtd_buspmt = transit_calcs.loc[transit_calcs['facility_type'] == '103', 'miles_tot'].sum().sum()
        rtd_carpmt = transit_calcs.loc[transit_calcs['facility_type'].isin(['1', '2', '3', '4', '5', '6', '7', '11', '12']), 'miles_tot'].sum().sum()
        # Transit wait times
        rtd_lrphtwait = transit_calcs.loc[transit_calcs['facility_type'] == '600', 'hours_tot'].sum().sum()
        rtd_hrphtwait = transit_calcs.loc[transit_calcs['facility_type'].isin(['601', '602']), 'hours_tot'].sum().sum()
        rtd_busphtwait = transit_calcs.loc[transit_calcs['facility_type'] == '603', 'hours_tot'].sum().sum()
        # Passenger travel times
        rtd_lrphtenroute = transit_calcs.loc[transit_calcs['facility_type'] == '100', 'hours_tot'].sum().sum()
        rtd_hrphtenroute = transit_calcs.loc[transit_calcs['facility_type'].isin(['101', '102']), 'hours_tot'].sum().sum()
        rtd_busphtenroute = transit_calcs.loc[transit_calcs['facility_type'] == '103', 'hours_tot'].sum().sum()
        rtd_carpht = transit_calcs.loc[transit_calcs['facility_type'].isin(['1', '2', '3', '4', '5', '6', '7', '11', '12']), 'hours_tot'].sum().sum()
    else:
        logger.info("Only calculating overall metrics for scenario {}".format(scenname))
        if cfg['aeq_run_type'] == 'RT':
            logger.info("If transit-specific benefits are desired, set calc_transit_metrics to 1 in the config file and use default facility type fields")
    
    # Write outputs to csv file
    outfile = open(join(disrupt_run_folder, "NetSkim.csv"), "w")
    # TODO: Create extra column headers if calc_transit_metrics (and print extra empty data values)
    if cfg['calc_transit_metrics']:
        print("Type,SP/RT,socio,projgroup,resil,elasticity,hazard,recovery,Scenario,trips,miles,hours," +
              "lost_trips,extra_miles,extra_hours,circuitous_trips_removed,lr_trips,hr_trips,bus_trips," +
              "car_trips,lr_miles,hr_miles,bus_miles,car_miles,lr_hours_wait,hr_hours_wait,bus_hours_wait," +
              "lr_hours_enroute,hr_hours_enroute,bus_hours_enroute,car_hours", file=outfile)
    else:
        print("Type,SP/RT,socio,projgroup,resil,elasticity,hazard,recovery,Scenario,trips,miles,hours," +
              "lost_trips,extra_miles,extra_hours,circuitous_trips_removed", file=outfile)
    print("Base,SP," + socio + ',' + projgroup + ',' + resil + ',' + str(elasticity) + ',' + hazard + ',' + recovery +
          ',' + basescenname + ',' + '{:.8},{:.8},{:.8}'.format(spb_cumtripcount, spb_cumdist, spb_cumtime/60),
          file=outfile)
    lost_trips = spb_cumtripcount - spd_cumtripcount
    extra_mi = spd_cumdist - spd_basecumdist
    extra_hr = (spd_cumtime - spd_basecumtime)/60
    print("Disrupt,SP," + socio + ',' + projgroup + ',' + resil + ',' +
          str(elasticity) + ',' + hazard + ',' + recovery + ',' + scenname + ',' +
          '{:.8},{:.8},{:.8},{:.8},{:.8},{:.8},{:.8}'.format(spd_cumtripcount, spd_cumdist, spd_cumtime/60, lost_trips,
                                                             extra_mi, extra_hr, circuitous_trips_removed),
          file=outfile)
    print("Base,RT," + socio + ',' + projgroup + ',' + resil + ',' + str(elasticity) + ',' + hazard + ',' + recovery +
          ',' + basescenname + ',' + '{:.8},{:.8},{:.8}'.format(rtb_cumtripcount, rtb_cumdist, rtb_cumtime/60),
          file=outfile)
    lost_trips = rtb_cumtripcount - rtd_cumtripcount
    extra_mi = rtd_cumdist - rtd_basecumdist
    extra_hr = (rtd_cumtime - rtd_basecumtime)/60
    # Add extra calculated values if calc_transit_metrics is True
    if cfg['calc_transit_metrics']:
        # circuitous_trips_removed is set as 0.0 for a placeholder
        print("Disrupt,RT," + socio + ',' + projgroup + ',' + resil + ',' +
              str(elasticity) + ',' + hazard + ',' + recovery + ',' + scenname + ',' +
              '{:.8},{:.8},{:.8},{:.8},{:.8},{:.8},{:.8},'.format(rtd_cumtripcount, rtd_cumdist, rtd_cumtime/60, lost_trips,
                                                            extra_mi, extra_hr, 0.0) +
              '{:.8},{:.8},{:.8},{:.8},{:.8},{:.8},{:.8},{:.8},'.format(rtd_lrtrips, rtd_hrtrips, rtd_bustrips, rtd_cartrips,
                                                                        rtd_lrpmt, rtd_hrpmt, rtd_buspmt, rtd_carpmt) +
              '{:.8},{:.8},{:.8},{:.8},{:.8},{:.8},{:.8}'.format(rtd_lrphtwait, rtd_hrphtwait, rtd_busphtwait,
                                                                 rtd_lrphtenroute, rtd_hrphtenroute, rtd_busphtenroute,
                                                                 rtd_carpht), file=outfile)
    else:
        print("Disrupt,RT," + socio + ',' + projgroup + ',' + resil + ',' +
              str(elasticity) + ',' + hazard + ',' + recovery + ',' + scenname + ',' +
              '{:.8},{:.8},{:.8},{:.8},{:.8},{:.8}'.format(rtd_cumtripcount, rtd_cumdist, rtd_cumtime/60, lost_trips,
                                                           extra_mi, extra_hr), file=outfile)

    # Reporting run statistics to log file
    logger.debug("total pht: {}  average per trip: {}".format(spb_cumtime/60, spb_cumtime/60/df_dem.sum().sum()))
    logger.debug("total pmt: {}  average per trip: {}".format(spb_cumdist, spb_cumdist/df_dem.sum().sum()))

    logger.debug("total pht: {}  average per trip: {}".format(rtb_cumtime/60, rtb_cumtime/60/df_dem.sum().sum()))
    logger.debug("total pmt: {}  average per trip: {}".format(rtb_cumdist, rtb_cumdist/df_dem.sum().sum()))

    logger.debug("total disrupt_pht: {}  average per trip: {}".format(spd_cumtime/60,
                                                                      spd_cumtime/60/df_newdem.sum().sum()))
    logger.debug("total disrupt_pmt: {}  average per trip: {}".format(spd_cumdist, spd_cumdist/df_newdem.sum().sum()))

    logger.debug("total disrupt_pht: {}  average per trip: {}".format(rtd_cumtime/60,
                                                                      rtd_cumtime/60/df_newdem.sum().sum()))
    logger.debug("total disrupt_pmt: {}  average per trip: {}".format(rtd_cumdist, rtd_cumdist/df_newdem.sum().sum()))

    # Close the files

    spdf.close()
    rtdf.close()
    f.close()
    nf.close()
    spbf.close()
    rtbf.close()
    outfile.close()
    project.close()


# ==============================================================================


def get_output_demand(t_disrupt, t_base, input_demand, large_value, power_factor):
    base_df = pd.DataFrame(data=t_base)
    disrupt_df = pd.DataFrame(data=t_disrupt)
    input_demand_df = pd.DataFrame(data=input_demand)

    # calculate trips_removed
    na_df = disrupt_df.isna()
    large_df = disrupt_df > large_value
    bool_trips_to_remove_df = na_df | large_df
    trips_removed = (input_demand_df*bool_trips_to_remove_df).sum().sum()

    bool_trips_to_keep_df = (disrupt_df - base_df < .5) & ~bool_trips_to_remove_df
    trips_unchanged = (input_demand_df*bool_trips_to_keep_df).sum().sum()

    bool_trips_to_reduce_df = ~(bool_trips_to_keep_df | bool_trips_to_remove_df)
    # this bool condition replaces the "else" in the original loop
    # matrix is zeros except for trips being transformed
    draft_output_df = (input_demand_df*pow((disrupt_df/base_df), power_factor)).where(bool_trips_to_reduce_df, 0)

    trips_reduced = (input_demand_df*bool_trips_to_reduce_df).sum().sum()
    output_trips_reduced = draft_output_df.sum().sum()

    output_df = draft_output_df + (input_demand_df*bool_trips_to_keep_df)

    return output_df, (trips_removed, trips_unchanged, trips_reduced, output_trips_reduced)
