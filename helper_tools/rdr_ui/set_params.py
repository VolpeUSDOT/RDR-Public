import argparse
import os

import ui
import ui_tools as ut
import params

def main(go_to:str = params.current_param.value, load_save:bool = False) -> None:
    if load_save:
        uinput, go_to = ut.load_save(params.save_file, params.param_list)
        if uinput != '':    
            params.save_file.value = uinput

    if go_to in params.hidden_shorts:
        set_hidden()

    if go_to == 'next':
        go_to = ''.join([params.current_param.value, 'next'])

    start_page(go_to)

# ===================
# START
# ===================

def start_page(go_to:str = 'sequential'):

    if go_to in ['start', 'sequential']:
        print('\n\n\n\n   SET PARAMETERS\n\n   This series of prompts will walk you through the setup of an RDR scenario. Use universal commands at any point.\n   To skip a parameter without assigning a value, simply press Enter with no other keyboard inputs')
        print('\n    To save, type -save at any point. For help, type -help at any point.')
        uinput = input('\n\n\n\n   Press Enter to continue')
        ui.universal_commands(uinput)

    os.system('cls')
    set_dirs(go_to)

# ===================
# COMMON VALUES
# ===================

def set_dirs(go_to:str = 'sequential'):
    parameter = params.input_dir
    message = 'Provide the RDR input directory.'
    if go_to in [parameter.short, ''.join([parameter.short, 'backto']), 'sequential']:   
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, fn_or_dir = 'directory', should_exist = True)
        if uinput != '':    
            parameter.value = uinput
        if 'backto' in go_to:
            ui.build_bat()
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.output_dir
    message = 'Provide the RDR output directory.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, fn_or_dir = 'directory', should_exist = False)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.run_id
    message = 'Set a Run ID for this RDR run.'
    if go_to in [parameter.short, ''.join([parameter.short, 'backto']), 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, char_floor = 1, char_ceiling = 100, illegal_chars = [])
        if uinput != '':    
            parameter.value = uinput
        if 'backto' in go_to:
            ui.build_bat()
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_years(go_to)

def set_years(go_to:str = 'sequential'):
    parameter = params.start_year
    message = 'Enter the analysis period start year.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 1000, high = 9999)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short
        
    parameter = params.end_year
    message = 'Enter the analysis period end year.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 1000, high = 9999)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.base_year
    message = 'Enter the base year for core model runs.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 1000, high = 9999)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.future_year
    message = 'Enter the future year for core model runs.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 1000, high = 9999)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_metamodel_1(go_to)

# ===================
# METAMODEL VALUES
# ===================

def set_metamodel_1(go_to:str = 'sequential'):
    parameter = params.metamodel_type
    message = 'Select which metamodel method to use.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short
    
    parameter = params.lhs_sample_target
    message = 'Set the Latin hypercube sample size.\n\nDefines the number of scenarios identified by the Latin hypercube sampling algorithm to generate AequilibraE outputs for.\nThe RDR metamodel is highly sensitive to this parameter. See the User Guide for details on selecting an appropriate value.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 1, high = 1000000000000000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_metamodel_2(go_to)

def set_metamodel_2(go_to:str = 'sequential'):
    parameter = params.aeq_run_type
    message = 'Set AequilibraE model run type. SP is shortest path and RT is routing (default).'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.run_minieq
    message = 'Mini-Equilibrium Run Selection\n0 (default) will run the routing code only once. 1 will run mini-equilibrium setup for routing code.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.allow_centroid_flows
    message = 'AequilibraE Paths Through Centroids\n0 prevents Aequilibrae flows from routing through centroids/centroid connectors.\n1 (default) allows these flows.\nThis parameter should be set to 1 if the user wants to model multimodal trips.\nIn this case, centroid connector costs should be set appropriately high.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.calc_transit_metrics
    message = 'Calculate Transit-Specific Metrics\n0 considers all trips equally.\n1 (default) calculates and monetizes transit trips separately from car trips.\nUsers incorporating a transit network into their run are highly encouraged to use 1.\nIf calculating transit-specific metrics, the default facility types must be used and\nthe AequilibraE Model Run Type (as defined above) must be set to "RT" for routing.\nUsers specifying custom facility types in their network should use 0 to avoid misattribution errors.\nSee the User Guide for more details.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short
    
    os.system('cls')
    set_disruption_1(go_to)

# ===================
# DISRUPTION VALUES
# ===================

def set_disruption_1(go_to:str = 'sequential'):

    parameter = params.link_availability_approach
    message = "Select the link availability approach, which is the approach used to convert exposure \nto a specific level of disruption for each individual segment in the network. Options are: \n'Binary' (default) = Any value > 0 will be considered full exposure and link will not be available. Other links will remain fully available. \n'Default_Flood_Exposure_Function' = Utilize depth-disruption function adapted from Pregnolato et al. \n'Manual' = Develop your own bins for converting exposure into link availability based on template CSV provided with tool suite. \n'Facility_Type_Manual' = Develop your own bins for each facility type representing converting exposure into link availability based on template CSV provided with tool suite. \n'Beta_Distribution_Function' = Develop custom function converting exposure to disruption--based on Python's beta distribution function implementation."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.exposure_field
    message = 'Exposure Field\nField name in the exposure dataset (hazard CSV file) which defines exposure level.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, char_floor = 0, char_ceiling = 100, illegal_chars = [])
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    if params.link_availability_approach.value == 'manual' or params.link_availability_approach.value == 'facility_type_manual':
        parameter = params.link_availability_csv
        message = 'Set the path to the link availability CSV file.'
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    if params.link_availability_approach.value == 'beta_distribution_function':
        parameter = params.alpha
        message = 'Alpha - A number greater than 0 that helps define the shape of the beta distribution. \nFor use in the "beta_distribution_function" link_availability_approach to convert a hazard to a disruption.'
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000000000000000000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    os.system('cls')
    set_disruption_beta(go_to)

def set_disruption_beta(go_to:str = 'sequential'):

    if params.link_availability_approach.value == 'beta_distribution_function':
        parameter = params.beta
        message = 'Beta - A number greater than 0 that helps define the shape of the beta distribution. \nFor use in the "beta_distribution_function" link_availability_approach to convert a hazard to a disruption.'
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000000000000000000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    if params.link_availability_approach.value == 'beta_distribution_function':
        parameter = params.lower_bound
        message = "Lower Bound \nThe exposure value where link availability reaches 0% (if 'lower cumulative' beta distribution function is utilized) \nor 100% (if 'upper cumulative' beta distribution function is utilized). \nFor use in the 'beta_distribution_function' link_availability_approach to convert a hazard to a disruption."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000000000000000000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short
    
    if params.link_availability_approach.value == 'beta_distribution_function':
        parameter = params.upper_bound
        message = "Upper Bound \nThe exposure value where link availability reaches 100% (if 'lower cumulative' beta distribution function is utilized) \nor 0% (if 'upper cumulative' beta distribution function is utilized). \nFor use in the 'beta_distribution_function' link_availability_approach to convert a hazard to a disruption."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000000000000000000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    if params.link_availability_approach.value == 'beta_distribution_function':
        parameter = params.beta_method
        message = "Beta Method \nUser can select 'lower cumulative' or 'upper cumulative'. \nIf 'lower cumulative', link availability reaches 0 percent at lower bound and 100 percent at the upper bound. \nIf 'upper cumulative', link availability reaches 100 percent at lower bound and 0 percent at upper bound. \nIn either method, link availability will always be 100 percent for links with no (NULL) hazard exposure."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    os.system('cls')
    set_disruption_2(go_to)

def set_disruption_2(go_to:str = 'sequential'):

    parameter = params.highest_zone_number
    message = 'Designated Centroid Nodes \nDefines the highest node ID designated as a centroid node. \nLinks connecting one or more centroid nodes are treated as zone connectors and are not impacted by hazard events. \nDefault value is 0 (i.e., no centroid nodes) if left blank.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 10000000000000000000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.resil_mitigation_approach
    message = "Resilience Mitigation Approach \nDefines the approach used to convert investment in a resilience project to mitigation of exposure and disruption on the network. \n'Binary' (default) = Investment in a resilience project will lead to associated network links experiencing full exposure reduction and no disruption across all hazards. \n'Manual' = Mitigation from a resilience project investment is specified for each associated network link in an 'Exposure Reduction' column of the project table input file."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_recovery_1(go_to)

# ===================
# RECOVERY VALUES
# ===================

def set_recovery_1(go_to:str = 'sequential'):

    parameter = params.num_recovery_stages
    message = 'Set the number of hazard recovery stages.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 1000000000000000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.min_duration
    message = 'Set the minimum duration of initial hazard event [days]. \nThis defines the minimum number of days a hazard event may last at the initial hazard severity.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 1, high = 1000000000000000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.max_duration
    message = 'Set the maximum duration of initial hazard event [days]. \nThis defines the maximum number of days a hazard event may last at the initial hazard severity.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 1, high = 1000000000000000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.num_duration_cases
    message = 'Set the number of hazard duration cases to run. \nThis defines the number of potential hazard durations to analyze with the RDR Tool Suite.'
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 1, high = 1000000000000000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.hazard_recov_type
    message = "Hazard Recovery Build-out Type \nUser can select 'days' or 'percent'. \nIf 'days', the hazard recovery period (e.g., period after initial hazard severity and before end of hazard) is specified in number of days. \nIf 'percent', the hazard recovery period is specified as a percentage of the duration of the initial hazard severity."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_recovery_2(go_to)

def set_recovery_2(go_to:str = 'sequential'):

    parameter = params.hazard_recov_length
    message = "Hazard Recovery Build-out Length \nDefines the length of the hazard recovery period in either number of days or as a percentage (as specified in Hazard Recovery Build-out Type above)."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 1000000000000000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.hazard_recov_path_model
    message = "Hazard Recovery Path Model \nDefines the approach used to construct hazard recovery path from initial hazard severity through the end of the hazard event. \n'Equal' (default) = Hazard recovery stages are of equal length. \nOther options may be added in the future."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.exposure_damage_approach
    message = "Exposure-Damage Approach \nDefines the approach used to convert exposure to a specific level of asset damage. \n'Binary' (default) = Any value > 0 will be considered full damage to link. Other links will incur no damage. \n'Default_Damage_Table' = Utilize depth-damage functions adapted from Simonovic et al. for flood-based hazard events on roadways and bridges. Utilize depth-damage function adapted from Martello et al. for transit flooding events. Full references available in the Technical Documentation. \n'Manual' = Develop your own bins representing converting exposure into link damage based on template CSV provided with tool suite."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    if params.link_availability_approach.value == 'default_flood_exposure_function' or params.exposure_damage_approach.value == 'default_damage_table':
        parameter = params.exposure_unit
        message = 'Enter the units for the exposure field. \nAcceptable units are feet, meters, or yards. The "exposure_field" defined already by the user is ' + params.exposure_field.value + '.'
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    os.system('cls')
    set_recovery_3(go_to)

def set_recovery_3(go_to:str = 'sequential'):

    if params.exposure_damage_approach.value == 'manual':
        parameter = params.exposure_damage_csv
        message = 'Set the path to the exposure damage table CSV file, for use in the "manual" exposure-damage approach.'
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    parameter = params.repair_cost_approach
    message = "Enter the repair cost approach \nDefines the approach used to convert asset damage to cost of repair. \nUser can select 'default' or 'user-defined'."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    if params.repair_cost_approach.value == 'default':
        parameter = params.repair_network_type
        message = "Enter the network type \nUser can select 'Rural Flat', 'Rural Rolling', 'Rural Mountainous', 'Small Urban' (populations of 5,000 to 49,999), \n'Small Urbanized' (populations of 50,000 to 200,000), 'Large Urbanized' (populations of more than 200,000), \n'Major Urbanized' (populations of more than 1,000,000)."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    if params.repair_cost_approach.value == 'user-defined':
        parameter = params.repair_cost_csv
        message = "Set the path to the repair cost CSV file, for use in the 'user-defined' repair cost approach."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    parameter = params.repair_time_approach
    message = "Set the repair time approach. \nDefines the approach used to convert asset damage to minimum time to repair. \nUser can select 'default' or 'user-defined'."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    if params.repair_time_approach.value == 'user-defined':
        parameter = params.repair_time_csv
        message = "Set the path to the repair time CSV file, for use in the 'user-defined' repair time approach."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    os.system('cls')
    set_analysis_1(go_to)

# ===================
# ANALYSIS VALUES
# ===================

def set_analysis_1(go_to:str = 'sequential'):

    parameter = params.roi_analysis_type
    message = "ROI Analysis Type \nDefines the ROI analysis type run by RDR. User can select 'BCA', 'Regret', or 'Breakeven'. \nSee the Technical Documentation for specifications and required inputs for each ROI analysis type."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.dollar_year
    message = "Year for Dollar Units \nSpecifies the year in which all monetary benefit/cost units are input and reported. Costs include: \n(1) vehicle operating costs, value of travel time, value of transit wait time, and transit fare in configuration file, \n(2) project costs, redeployment costs (optional), and maintenance costs (optional) in project_info.csv input file, \n(3) repair costs in repair costs table (default or user-defined), \n(4) network link tolls in link tables (optional), \n(5) safety, noise, and emissions monetization values (default or user-defined)."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 1000, high = 9999)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.discount_factor
    message = "Year-on-Year Discounting Factor \nDefines the discounting factor used to convert metrics across entire period of analysis to year specified for dollar units. \nU.S. DOT recommended value is 0.031. Value should be entered as a decimal, not a percent."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 1)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.co2_discount_factor
    message = "Year-on-Year CO2 Discounting Factor \nDefines the CO2-specific discounting factor used to convert metrics across entire period of analysis to year specified for dollar units. \nU.S. DOT recommended value is 0.02. Value should be entered as a decimal, not a percent."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 1)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_analysis_2(go_to)

def set_analysis_2(go_to:str = 'sequential'):

    parameter = params.vehicle_occupancy_car
    message = "Vehicle Occupancy Rate for Passenger Vehicles [persons/vehicle] \nDefines average vehicle occupancy rates for passenger vehicles used to convert passenger-miles traveled to vehicle-miles traveled. \nU.S. DOT recommended value for passenger vehicle is 1.67."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 10000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    if params.calc_transit_metrics.value == 1:
        parameter = params.vehicle_occupancy_bus
        message = "Vehicle Occupancy Rate for Buses [persons/vehicle] \nDefines average vehicle occupancy rates for transit buses used to convert passenger-miles traveled to vehicle-miles traveled. \nFHWA-provided value for buses is 20."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    if params.calc_transit_metrics.value == 1:
        parameter = params.vehicle_occupancy_light_rail
        message = "Vehicle Occupancy Rate for transit light rail [persons/vehicle] \nDefines average vehicle occupancy rates for transit light rail used to convert passenger-miles traveled to vehicle-miles traveled."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    if params.calc_transit_metrics.value == 1:
        parameter = params.vehicle_occupancy_heavy_rail
        message = "Vehicle Occupancy Rate for transit heavy rail [persons/vehicle] \nDefines average vehicle occupancy rates for transit heavy rail used to convert passenger-miles traveled to vehicle-miles traveled."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    os.system('cls')
    set_analysis_3(go_to)

def set_analysis_3(go_to:str = 'sequential'):

    parameter = params.veh_oper_cost_car
    message = "Passenger Car Operating Costs [$/vehicle-mile] \nDefines the variable operating costs (e.g., gasoline, maintenance, tires, depreciation) for passenger vehicles per mile driven. \nU.S. DOT recommended value in 2022 dollars for light duty vehicles is 0.52."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 10000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    if params.calc_transit_metrics.value == 1:
        parameter = params.veh_oper_cost_bus
        message = "Transit Bus Operating Costs [$/vehicle-mile] \nDefines the variable operating costs (e.g., gasoline, maintenance, tires, depreciation, transit operator time) for transit buses per mile driven. \nThe FTA National Transit Database reports a value of 1.32 in 2022 dollars."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    if params.calc_transit_metrics.value == 1:
        parameter = params.veh_oper_cost_light_rail
        message = "Transit Light Rail Operating Costs [$/vehicle-mile] \nDefines the variable operating costs (e.g., gasoline, maintenance, tires, depreciation, transit operator time) for transit light rail per mile driven. \nThe FTA National Transit Database reports a value of 5.72 in 2022 dollars."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    if params.calc_transit_metrics.value == 1:
        parameter = params.veh_oper_cost_heavy_rail
        message = "Transit Heavy Rail Operating Costs [$/vehicle-mile] \nDefines the variable operating costs (e.g., gasoline, maintenance, tires, depreciation, transit operator time) for transit heavy rail per mile driven. \nThe FTA National Transit Database reports a value of 4.01 in 2022 dollars."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    os.system('cls')
    set_analysis_4(go_to)

def set_analysis_4(go_to:str = 'sequential'):

    parameter = params.vot_per_hour
    message = "Value of Travel Time [$/hour] \nDefines the value of time used to convert link tolls in the network to travel time and to convert person-hours traveled to dollars. \nU.S. DOT recommended value in 2022 dollars is 19.60."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 10000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short  

    if params.calc_transit_metrics.value == 1:
        parameter = params.vot_wait_per_hour
        message = "Value of Wait Time [$/hour] \nDefines the value of time used to convert transit wait time on boarding links in the network in person-hours to dollars. \nU.S. DOT recommended value in 2022 dollars is 35.80."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    if params.calc_transit_metrics.value == 1:
        parameter = params.transit_fare
        message = "Transit Fare [$/trip] \nDefines the value of a transit trip used to convert trips lost to dollars."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    parameter = params.maintenance
    message = "Indicate whether to include Annual Maintenance Cost \nAnnual maintenance costs are defined in the project_info.csv input file and are applied every year. \nIf set to True, an 'Annual Maintenance Cost' column is required in the project info input file. \nOptions: True or False. Default is False."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short 

    os.system('cls')
    set_analysis_5(go_to)

def set_analysis_5(go_to:str = 'sequential'):

    parameter = params.redeployment
    message = "Indicate whether to include Redeployment Cost \nRedeployment costs are defined in the project_info.csv input file and are applied every project lifespan AFTER the initial project deployment. \nIf set to True, a 'Redeployment Cost' column is required in the project info input file. \nOptions: True or False. Default is False."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.safety_cost
    message = "Light Duty Safety Costs [$/vehicle-mile] \nDefines the safety external highway use costs per mile driven divided by external share for light duty vehicles. \nU.S. DOT recommended value in 2022 dollars for light duty vehicles in urban location is 0.17."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 10000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    if params.calc_transit_metrics.value == 1:
        parameter = params.safety_cost_bus
        message = "Bus Safety Costs [$/vehicle-mile] \nDefines the safety external highway use costs per mile driven divided by external share for transit buses. \nU.S. DOT recommended value in 2022 dollars for buses in urban location is 0.094."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    parameter = params.noise_cost
    message = "Light Duty Noise Costs [$/vehicle-mile] \nDefines the noise external highway use costs per mile driven for light duty vehicles. \nU.S. DOT recommended value in 2022 dollars for light duty vehicles in urban location is 0.0019."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 10000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_analysis_6(go_to)

def set_analysis_6(go_to:str = 'sequential'):

    if params.calc_transit_metrics.value == 1:
        parameter = params.noise_cost_bus
        message = "Bus Noise Costs [$/vehicle-mile] \nDefines the noise external highway use costs per mile driven for transit buses. \nU.S. DOT recommended value in 2022 dollars for buses in urban location is 0.0437."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    parameter = params.non_co2_cost
    message = "Light Duty Non-CO2 Emissions Costs [$/vehicle-mile] \nDefines the non-CO2 emissions external highway use costs per mile driven for light duty vehicles. \nU.S. DOT recommended value in 2022 dollars for light duty vehicles in any location is 0.012."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 10000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_analysis_7(go_to)

def set_analysis_7(go_to:str = 'sequential'):

    if params.calc_transit_metrics.value == 1:
        parameter = params.non_co2_cost_bus
        message = "Bus Non-CO2 Emissions Costs [$/vehicle-mile] \nDefines the non-CO2 emissions external highway use costs per mile driven for transit buses. \nU.S. DOT recommended value in 2022 dollars for buses in any location is 0.035."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    parameter = params.co2_cost
    message = "Light Duty CO2 Emissions Costs [$/vehicle-mile] \nDefines the CO2 emissions external highway use costs per mile driven for light duty vehicles. \nU.S. DOT recommended value in 2022 dollars for light duty vehicles in urban location is 0.107."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, low = 0, high = 10000)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    if params.calc_transit_metrics.value == 1:
        parameter = params.co2_cost_bus
        message = "Bus CO2 Emissions Costs [$/vehicle-mile] \nDefines the CO2 emissions external highway use costs per mile driven for transit buses. \nU.S. DOT recommended value in 2022 dollars for buses in urban location is 0.303."
        if go_to in [parameter.short, 'sequential']:
            params.current_param.value = parameter.short
            uinput = ut.build_input(parameter, message, low = 0, high = 10000)
            if uinput != '':
                parameter.value = uinput
            go_to = 'sequential'
            params.previous_param.value = parameter.short

    os.system('cls')
    set_haz(go_to)

# ===================
# NON-CONFIG
#====================
    
# MultiParams

def set_haz(go_to:str = 'sequential'):
    parameter = params.hazards
    message = "Hazards name, file path, hazard dimension 1, hazard dimension 2, hazard probability"
    info = ""
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, info, mlist = params.haz_minis_list)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short
    elif go_to == ''.join([parameter.short, 'next']):
        go_to = 'sequential'

    os.system('cls')
    set_eff(go_to)            

def set_eff(go_to:str = 'sequential'):
    parameter = params.event_frequency_factors
    message = "Event frequency factor"
    info = "Enter only one event frequency factor numeric value per event frequency factor (press Enter key between value entries)"
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, info, mlist = params.eff_minis_list)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short
    elif go_to == ''.join([parameter.short, 'next']):
        go_to = 'sequential'

    os.system('cls')
    set_ecf(go_to)

def set_ecf(go_to:str = 'sequential'):
    parameter = params.economic_futures
    message = "Economic futures name, file path to associated OMX file"
    info = ""
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, info, mlist = params.ecf_minis_list)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short
    elif go_to == ''.join([parameter.short, 'next']):
        go_to = 'sequential'

    os.system('cls')
    set_tle(go_to)

def set_tle(go_to:str = 'sequential'):
    parameter = params.trip_loss_elasticities
    message = "Trip loss elasticity (typical value expected is between -1 and 0)"
    info = "Enter only one trip loss elasticity numeric value per trip loss elasticity (press Enter key between value entries)"
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, info, mlist = params.tle_minis_list)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short
    elif go_to == ''.join([parameter.short, 'next']):
        go_to = 'sequential'

    os.system('cls')
    set_rep(go_to)

def set_rep(go_to:str = 'sequential'):
    parameter = params.resilience_projects
    message = "Resilience projects name, project group"
    info = ""
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, info, mlist = params.rep_minis_list)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short
    elif go_to == ''.join([parameter.short, 'next']):
        go_to = 'sequential'

    os.system('cls')
    set_netlink(go_to)

def set_netlink(go_to:str = 'sequential'):  # Should not be able to jump to this without setting rep and ecf
    parameter = params.network_links
    message = "File paths to network links files for each resilience project group and economic scenario pair (i.e., base02.csv as seen in Quick Start 1 /Data/inputs/Networks folder)"
    info = ""
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, info, mlist = params.net_minis_list)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short
    elif go_to == ''.join([parameter.short, 'next']):
        go_to = 'sequential'

    os.system('cls')
    set_other_1(go_to)

## Single Params

def set_other_1(go_to:str = 'sequential'):
    parameter = params.net_node
    message = "Path to the network node CSV file"
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.proj_table
    message = "Path to project link CSV file (project_table.csv)"
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.proj_info
    message = "Path to project costs CSV file (project_info.csv)"
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_other_2(go_to)

def set_other_2(go_to:str = 'sequential'):
    # if params.maintenance.value or go_to == params.maintenance_column.short:
    #     parameter = params.maintenance_column
    #     message = "Name of the annual maintenance column in the project costs file"
    #     if go_to in [parameter.short, 'sequential']:
    #         params.current_param.value = parameter.short
    #         uinput = ut.build_input(parameter, message, char_floor = 1, char_ceiling = 100, illegal_chars = [])
    #         if uinput != '':
    #             parameter.value = uinput
    #         go_to = 'sequential'
    #         params.previous_param.value = parameter.short

    # if params.redeployment.value or go_to == params.redeployment_column.short:
    #     parameter = params.redeployment_column
    #     message = "Name of the redeployment column in the project costs file"
    #     if go_to in [parameter.short, 'sequential']:
    #         params.current_param.value = parameter.short
    #         uinput = ut.build_input(parameter, message, char_floor = 1, char_ceiling = 100, illegal_chars = [])
    #         if uinput != '':
    #             parameter.value = uinput
    #         go_to = 'sequential'
    #         params.previous_param.value = parameter.short

    parameter = params.base_year_file
    message = "Path to the base year CSV file. The base year core model runs must be provided in a file named 'Metamodel_scenario_{SP/RT}_baseyear.csv' where the bracketed text is either 'SP' or 'RT' as specified in the configuration file."
    if go_to in [parameter.short, 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
        if uinput != '':
            parameter.value = uinput
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    set_bat(go_to)

# ===================
# SET BAT VALUES
# ===================
    
def set_bat(go_to:str = 'sequential'):

    if go_to not in [params.python.short, params.rdr.short, params.bat_location.short, 'sequential']:
        os.system('cls')
        end_page(go_to)

    parameter = params.python
    message = "Set the file path for the python.exe associated with your RDR environment"
    if go_to in [parameter.short, ''.join([parameter.short, 'backto']), 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
        if uinput != '':
            parameter.value = uinput
        if 'backto' in go_to:
            ui.build_bat()
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.rdr
    message = "Set the file path for your Run_RDR.py file"
    if go_to in [parameter.short, ''.join([parameter.short, 'backto']), 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, fn_or_dir = 'filename', should_exist = True)
        if uinput != '':
            parameter.value = uinput
        if 'backto' in go_to:
            ui.build_bat()
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    parameter = params.bat_location
    message = "Set the folder path for the batch file for your RDR run"
    if go_to in [parameter.short, ''.join([parameter.short, 'backto']), 'sequential']:
        params.current_param.value = parameter.short
        uinput = ut.build_input(parameter, message, fn_or_dir = 'directory', should_exist = True)
        if uinput != '':
            parameter.value = uinput
        if 'backto' in go_to:
            ui.build_bat()
        go_to = 'sequential'
        params.previous_param.value = parameter.short

    os.system('cls')
    end_page(go_to)

# ===================
# END
# ===================
    
def end_page(go_to):
    if go_to == 'sequential':
        input('\n\n\n      Done setting RDR parameters. RDR will now save. Press Enter key to continue...')
        ut.quick_save(params.save_file, params.param_list, go_to = params.current_param.value)
        input('\n\n\n      Save successful. Press Enter key to return to Main Menu...')
        os.system('cls')
        ui.main_menu()
        
    print('       \n\n\n\nInvalid shortcut. Type -h for help.')

# ===================
# HIDDEN PARAMETERS
# ===================  

def set_hidden():

    parameter = params.seed
    message = 'WARNING: HIDDEN INTERNAL PARAMETER\nSet testing seed.'
    uinput = ut.build_input(parameter, message, char_floor = 0, char_ceiling = 1000000000000, illegal_chars = [])
    if uinput != '':
        parameter.value = uinput

    parameter = params.save_file
    message = 'WARNING: HIDDEN INTERNAL PARAMETER\nManually set save file path.'
    uinput = ut.build_input(parameter, message)
    if uinput != '':
        parameter.value = uinput

    parameter = params.current_param
    message = 'WARNING: HIDDEN INTERNAL PARAMETER\nManually set current parameter of the UI.'
    uinput = ut.build_input(parameter, message, char_floor = 0, char_ceiling = 1000000000000, illegal_chars = [])
    if uinput != '':
        parameter.value = uinput

    parameter = params.previous_param
    message = 'WARNING: HIDDEN INTERNAL PARAMETER\nManually set previous parameter of the UI.'
    uinput = ut.build_input(parameter, message, char_floor = 0, char_ceiling = 1000000000000, illegal_chars = [])
    if uinput != '':
        parameter.value = uinput
    
    parameter = params.dev_mode
    message = 'WARNING: HIDDEN INTERNAL PARAMETER\nSet developer mode. (Currently has no effect, change default value manually to True in params.py to launch RDR UI in developer mode.)'
    uinput = ut.build_input(parameter, message)
    if uinput != '':
        parameter.value = uinput

if __name__ == "__main__":
    main()
