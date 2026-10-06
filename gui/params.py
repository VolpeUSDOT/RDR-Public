dtypes = ['str', 'path', 'year', 'options', 'int', 'float', 'multi']  # Add new dtypes as needed. Do not create dtypes that are used less than twice.

param_list = []  # param_list is simply the list of pointers to the Param objects in memory. Modification of the Param objects via the param_list is not advised.

class Param:
    def __init__(self, name:str, title:str = "", refnum:str = "", desc:str = "", dtype:str = 'str', value = None, mval:list = None, required:bool = True, options:list = None, short:str = None, docs:str = None):
        self.name = name
        self.title = title
        self.refnum = refnum
        self.desc = desc
        self.dtype = dtype
        self.value = value
        self.mval = mval
        self.required = required
        self.options = options
        self.short = short
        self.docs = docs
    def attributes(self):
        info = {}
        for key, val in self.__dict__.items():
            if val is not None:
                info[key] = val
        return info

class MultiParam:
    def __init__(self, name:str = None, fpath:str = None, dim1 = None, dim2 = None, value = None, group = None, prob:float = None, short:str = None):
        self.name = name,
        self.fpath = fpath
        self.dim1 = dim1
        self.dim2 = dim2
        self.value = value
        self.group = group
        self.prob = prob
        self.short = short
    def attributes(self):
        info = {}
        for key, val in self.__dict__.items():
            if val is not None:
                info[key] = val
        return info
    def write_attributes(self, input_dict):
        for key, val in input_dict.items():
            self.__dict__[key] = val    

# TODO: need to add rule for entering shorts, like typing 'short' before

# ===================
# COMMON VALUES
# ===================

input_dir = Param( ## Essential parameter
    'input_dir', 
    title = "Input Directory", 
    dtype = 'path', 
    short = 'in')
param_list.append(input_dir)

output_dir = Param( ## Essential parameter
    'output_dir', 
    title = "Output Directory", 
    dtype = 'path', 
    short = 'ou')
param_list.append(output_dir)

run_id = Param( ## Essential parameter
    'run_id', 
    title = "Run ID", 
    desc = """
    Denotes the string used to identify outputs for the run, e.g., run_id = 'SampleRun' means output files will be labeled 'SampleRun'.
    """, 
    short = 'id')
param_list.append(run_id)

analysis_period_start_year = Param( ## Essential parameter
    'analysis_period_start_year', 
    title = "Start Year of Analysis Period", 
    dtype = 'year', 
    short = 'sy')
param_list.append(analysis_period_start_year)

analysis_period_end_year = Param( ## Essential parameter
    'analysis_period_end_year', 
    title = "End Year of Analysis Period", 
    dtype = 'year', 
    short = 'ey')
param_list.append(analysis_period_end_year)

core_model_run_initial_year = Param( ## Essential parameter
    'core_model_run_initial_year', 
    title = "Year for Initial Year Core Model Runs",
    desc = """
    Specifies the initial year for trip table inputs and for which core model outputs are generated. Used in interpolation of results in economic analysis.
    """, 
    dtype = 'year', 
    short = 'by')
param_list.append(core_model_run_initial_year)

core_model_run_future_year = Param( ## Essential parameter
    'core_model_run_future_year', 
    title = "Year for Future Year Core Model Runs",
    desc = """
    Specifies the year for trip table inputs and for which core models are run on future scenarios. Used in interpolation of results in economic analysis.
    """,
    dtype = 'year', 
    short = 'fy')
param_list.append(core_model_run_future_year)

# ===================
# METAMODEL VALUES
# ===================

metamodel_type = Param(
    'metamodel_type',
    title = "Metamodel Type",
    desc = """
    State which metamodel method to use. See the User Guide for specifications of each metamodel method.
    """, 
    dtype = 'options', 
    value = 'multitarget', 
    required = False, 
    options = ['linear', 'interact', 'projgroupLM', 'multitarget', 'mixedeffects'],
    short = 'met')
param_list.append(metamodel_type)

lhs_sample_target = Param( ## Essential parameter
    'lhs_sample_target', 
    title = "Latin Hypercube Sample Size",
    desc = """
    Defines the number of scenarios identified by the Latin hypercube sampling algorithm to generate AequilibraE outputs for. 
      \nThe RDR model is highly sensitive to this parameter. See the User Guide for details on selecting an appropriate value.
    """,
    dtype = 'int', 
    short = 'lhs')
param_list.append(lhs_sample_target)

aeq_run_type = Param(
    'aeq_run_type', 
    title = "AequilibraE Model Run Type",
    desc = """
    Defines the type of AequilibraE run used to fit the metamodel. User can select 'SP' for shortest path or 'RT' for routing (default).
    """,
    dtype = 'options', 
    value = 'RT', 
    required = False, 
    options = ['SP', 'RT'], 
    short = 'art')
param_list.append(aeq_run_type)

run_minieq = Param(
    'run_minieq', 
    title = "Mini-Equilibrium Run",
    desc = """
    User can select 1 to run mini-equilibrium setup for routing code or 0 to run routing code only once (default).
    """,
    dtype = 'options', 
    value = 0, 
    required = False, 
    options = [0, 1], 
    short = 'rme')
param_list.append(run_minieq)

allow_centroid_flows = Param(
    'allow_centroid_flows', 
    title = "AequilibraE Paths Through Centroids",
    desc = """
    User can select 1 to allow flows to be routed through centroids/centroid connectors (default) or 0 to block these types of paths. 
      \nThis parameter should be set to 1 if the user wants to model multimodal trips. In this case, centroid connector costs should be set appropriately high.
    """,
    dtype = 'options', 
    value = 1, 
    required = False, 
    options = [0, 1], 
    short = 'acf')
param_list.append(allow_centroid_flows)

calc_transit_metrics = Param(
    'calc_transit_metrics', 
    title = "Calculate Transit-Specific Metrics",
    desc = """
    User can select 1 to calculate and monetize transit trips separately from car trips (default) or 0 to consider all trips equally.
      \nUsers incorporating a transit network into their run are highly encouraged to select 1.
      \nIf calculating transit-specific metrics, the default facility types must be used and the AequilibraE Model Run Type (as defined above) must be set to 'RT' for routing.
      \nUsers specifying custom facility types in their network should select 0 to avoid misattribution errors. See the User Guide for more details.
    """,
    dtype = 'options', 
    value = 0, 
    required = False, 
    options = [0, 1], 
    short = 'ctm')
param_list.append(calc_transit_metrics)

aeq_max_iter = Param(
    'aeq_max_iter', 
    title = "AequilibraE Max Iterations for Traffic Assignment",
    desc = """
    Defines the number of iterations of traffic assignment run by AequilibraE. 
      \nA larger number will better ensure convergence of the traffic assignment model, but will increase runtime.
    """,
    dtype = 'int', 
    value = 100, 
    required = False, 
    short = 'ami')
param_list.append(aeq_max_iter)

aeq_rgap_target = Param(
    'aeq_rgap_target', 
    title = "AequilibraE Gap Threshold for Traffic Assignment",
    desc = """
    Defines the gap target threshold for traffic assignment run by AequilibraE. 
      \nA smaller number will better ensure convergence of the traffic assignment model, but will increase runtime.""",
    dtype = 'float', 
    value = 0.01, 
    required = False, 
    short = 'agt')
param_list.append(aeq_rgap_target)

# ===================
# DISRUPTION VALUES
# ===================

link_availability_approach = Param( ## Essential parameter
    'link_availability_approach',
    title = "Link Availability Approach",
    desc = """
    Defines the approach used to convert exposure to a specific level of disruption to each individual segment in the network.
      \n'Binary' (default) = Any value > 0 will be considered full exposure and link will not be available. Other links will remain fully available.
      \n'Default_Flood_Exposure_Function' = Utilize depth-disruption function adapted from Pregnolato et al.
      \n'Manual' = Develop your own bins for converting exposure into link availability based on template CSV provided with tool suite.
      \n'Facility_Type_Manual' = Develop your own bins for each facility type representing converting exposure into link availability based on template CSV provided with tool suite. Facility types not represented are assumed not disrupted.
      \n'Beta_Distribution_Function' = Develop custom function converting exposure to disruption--based on Python's beta distribution function implementation.
    """,
    dtype = 'options', 
    value = 'binary', 
    # required = False, # Originally not required, but deemed essential
    options = ['binary', 'default_flood_exposure_function', 'manual', 'facility_type_manual', 'beta_distribution_function'],
    short = 'laa')
param_list.append(link_availability_approach)

exposure_field = Param( ## Essential parameter
    'exposure_field',
    title = "Exposure Field",
    desc = """
    Field name in the exposure dataset which defines exposure level.
    Default is 'Value' but this may vary depending on the specific dataset."
    """,
    dtype = 'str', 
    value = 'Value', 
    short = 'exf')
param_list.append(exposure_field)

exposure_unit = Param( ## Conditional requirement
    'exposure_unit',
    title = "Exposure Unit",
    desc = """
    Only required if default flood exposure curve is being utilized or default damage table is being utilized (see Recovery section below).
    Acceptable units are feet, meters, or yards.
    """,
    dtype = 'options', 
    required = False,
    options = ['feet', 'foot', 'ft', 'yards', 'yard', 'm', 'meters'], 
    short = 'exu') # Required if default flood exposure curve or default damage table is being used
param_list.append(exposure_unit)

link_availability_csv = Param( ## Conditional requirement
    'link_availability_csv', 
    title = "Path to Link Availability CSV",
    dtype = 'path', 
    required = False,
    short = 'lap')  # Required if link_availability_approach == 'manual' or 'facility_type_manual'
param_list.append(link_availability_csv)

alpha = Param( ## Conditional requirement
    'alpha',
    title = "Alpha", 
    dtype = 'float', 
    required = False,
    short = 'alp')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(alpha)

beta = Param( ## Conditional requirement
    'beta', 
    title = "Beta",
    dtype = 'float',
    required = False, 
    short = 'bet')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(beta)

lower_bound = Param( ## Conditional requirement
    'lower_bound', 
    title = "Lower Bound",
    desc = """
    The exposure value where link availability reaches 0% (if 'lower cumulative' beta distribution function is utilized) or 100% (if 'upper cumulative' beta distribution function is utilized).
    """,
    dtype = 'float', 
    required = False,
    short = 'lob')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(lower_bound)

upper_bound = Param( ## Conditional requirement
    'upper_bound',
    title = "Upper Bound",
    desc = """
    The exposure value where link availability reaches 100% (if 'lower cumulative' beta distribution function is utilized) or 0% (if 'upper cumulative' beta distribution function is utilized).
    """, 
    dtype = 'float', 
    required = False,
    short = 'upb')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(upper_bound)

beta_method = Param( ## Conditional requirement
    'beta_method', 
    title = "Beta Method",
    desc = f"""
    User can select 'lower cumulative' or 'upper cumulative'.
      \nIf 'lower cumulative', link availability reaches 0% at lower bound and 100% at upper bound.
      \nIf 'upper cumulative', link availability reaches 100% at lower bound and 0% at upper bound.
      \nIn either method, link availability will always be 100% for links with no (NULL) hazard exposure.
    """,
    dtype = 'options', 
    required = False,
    options = ['lower cumulative', 'upper cumulative'], 
    short = 'bem')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(beta_method)

highest_zone_number = Param( ## Essential parameter
    'highest_zone_number',  
    title = "Designated Centroid Nodes",
    desc = """
    Defines the highest node ID designated as a centroid node.
      \nLinks connecting one or more centroid nodes are treated as zone connectors and are not impacted by hazard events.
    """,
    dtype = 'int', 
    value = 0, 
    # required = False, # Originally not required, but deemed essential
    short = 'zoc')
param_list.append(highest_zone_number)

resil_mitigation_approach = Param(
    'resil_mitigation_approach',  
    title = "Resilience Mitigation Approach",
    desc = """
    Defines the approach used to convert investment in a resilience project to mitigation of exposure and disruption on the network.
      \n'Binary' (default) = Investment in a resilience project will lead to associated network links experiencing full exposure reduction and no disruption across all hazards.
      \n'Manual' = Mitigation from a resilience project investment is specified for each associated network link in an 'Exposure Reduction' column of the project table input file.
    """,
    dtype = 'options', 
    value = 'binary', 
    required = False, 
    options = ['binary', 'manual'],
    short = 'rma')
param_list.append(resil_mitigation_approach)

# ===================
# RECOVERY VALUES
# ===================

num_recovery_stages = Param( ## Essential parameter
    'num_recovery_stages',  
    title = "Number of Recovery Stages",
    dtype = 'int', 
    short = 'nrs')
param_list.append(num_recovery_stages)

min_duration = Param( ## Essential parameter
    'min_duration',  
    title = "Minimum Duration of Hazard Event [days]",
    desc = """
    Defines the minimum number of days a hazard event may last at the initial hazard severity.
    """,
    dtype = 'float', 
    short = 'mid')
param_list.append(min_duration)

max_duration = Param( ## Essential parameter
    'max_duration', 
    title = "Maximum Duration of Hazard Event [days]",
    desc = """
    Defines the maximum number of days a hazard event may last at the initial hazard severity.
    """, 
    dtype = 'float', 
    short = 'mad')
param_list.append(max_duration)

num_duration_cases = Param( ## Essential parameter
    'num_duration_cases',  
    title = "Number of Hazard Duration Cases to Run",
    desc = """
    Defines the number of potential hazard durations to analyze with the RDR Tool Suite.
    """,
    dtype = 'int', 
    short = 'ndc')
param_list.append(num_duration_cases)

hazard_recov_type = Param( ## Essential parameter
    'hazard_recov_type',  
    title = "Hazard Recovery Build-out Type",
    desc = """
    If 'days', the hazard recovery period (e.g., period after initial hazard severity and before end of hazard) is specified in number of days.
      \nIf 'percent', the hazard recovery period is specified as a percentage of the duration of the initial hazard severity.
    """,
    dtype = 'options', 
    options = ['days', 'percent'], 
    short = 'hrt')
param_list.append(hazard_recov_type)

hazard_recov_length = Param( ## Essential parameter
    'hazard_recov_length',  
    title = "Hazard Recovery Build-out Length",
    desc = """
    Defines the length of the hazard recovery period in either number of days or as a percentage (as specified above).
    """,
    dtype = 'float', 
    short = 'hrl')
param_list.append(hazard_recov_length)

hazard_recov_path_model = Param( ## Essential parameter
    'hazard_recov_path_model',  
    title = "Hazard Recovery Path Model",
    desc = """
    Defines the approach used to construct hazard recovery path from initial hazard severity through the end of the hazard event.
      \n'Equal' (default) = Hazard recovery stages are of equal length.
      \nOther options may be added in the future.
    """,
    dtype = 'options', 
    value = 'equal', 
    options = ['equal'], 
    short = 'hrp')
param_list.append(hazard_recov_path_model)

exposure_damage_approach = Param(
    'exposure_damage_approach',  
    title = "Exposure-Damage Approach",
    desc = """
    Defines the approach used to convert exposure to a specific level of asset damage on each individual segment in the network.
      \n'Binary' (default) = Any value > 0 will be considered full damage to link. Other links will incur no damage.
      \n'Default_Damage_Table' = Utilize depth-damage functions adapted from Simonovic et al. for flood-based hazard events on roadways and bridges. Utilize depth-damage function adapted from Martello et al. for transit flooding events. Full references available in the Technical Documentation.
      \n'Manual_Bins' = Develop your own bins converting exposure to link damage based on template CSV provided with tool suite. Bins should cover all possible exposure values.
      \n'Manual_Linear' = Develop your own piecewise linear function converting exposure to link damage based on template CSV provided with tool suite. Damage percentages are highly recommended to range from 0 to 1 inclusive.
    """,
    dtype = 'options', 
    value = 'binary', 
    required = False, 
    options = ['binary', 'default_damage_table', 'manual_bins', 'manual_linear'], 
    short = 'eda')
param_list.append(exposure_damage_approach)

exposure_damage_csv = Param( ## Conditional requirement
    'exposure_damage_csv',  
    title = "Path to Exposure-Damage Table CSV",
    dtype = 'path', 
    required = False,
    short = 'edp') # Required if exposure-damage approach is 'manual'
param_list.append(exposure_damage_csv)

repair_cost_approach = Param( ## Essential parameter
    'repair_cost_approach',  
    title = "Repair Cost Approach",
    desc = """
    Defines the approach used to convert asset damage to cost of repair.
      \n'Default' = Utilize FHWA estimated costs for highway and bridge assets. Utilize Hurricane Sandy-based costs developed from a 2014 HNTB Amtrak report for transit assets. Full references available in the Technical Documentation.
      \n'User-Defined' = Develop your own look-up table converting damage to repair cost based on template CSV provided with tool suite.
    """,
    dtype = 'options', 
    value = 'default', 
    options = ['default', 'user-defined'], 
    short = 'rca')
param_list.append(repair_cost_approach)

repair_network_type = Param( ## Conditional requirement
    'repair_network_type',  
    title = "Network Type",
    desc = """
    Population cut offs:   \n'Small Urban' (populations of 5,000 to 49,999),   \n'Small Urbanized' (populations of 50,000 to 200,000),   \n'Large Urbanized' (populations of more than 200,000),   \n'Major Urbanized' (populations of more than 1,000,000)
    """,
    dtype = 'options', 
    required = False,
    options = ['Rural Flat', 'Rural Rolling', 'Rural Mountainous', 'Small Urban', 'Small Urbanized', 'Large Urbanized', 'Major Urbanized'],
    short = 'rnt') # Required if default repair cost table is being used (repair_cost_approach == 'default')
param_list.append(repair_network_type)

repair_cost_csv = Param( ## Conditional requirement
    'repair_cost_csv',  
    title = "Path to Repair Cost CSV",
    dtype = 'path', 
    required = False,
    short = 'rcp') # Required if repair_cost_approach == "user-defined"
param_list.append(repair_cost_csv)

repair_time_approach = Param( ## Essential parameter
    'repair_time_approach',  
    title = "Repair Time Approach",
    desc = """
    Defines the approach used to convert asset damage to minimum time to repair.
      \n'Default' = Utilize data provided by Virginia DOT for highway and bridge assets. Utilize Hurricane Sandy-based recovery times based on a 2017 FHWA report for transit assets. Full references available in the Technical Documentation.
      \n'User-Defined' = Develop your own look-up table converting damage to repair time based on template CSV provided with tool suite.
    """,
    dtype = 'options', 
    options = ['default', 'user-defined'], 
    short = 'rta')
param_list.append(repair_time_approach)

repair_time_csv = Param( ## Conditional requirement
    'repair_time_csv',  
    title = "Path to Repair Time CSV",
    dtype = 'path', 
    required = False,
    short = 'rtp') # Required if repair_time_apprach == 'user-defined'
param_list.append(repair_time_csv)

# ===================
# ANALYSIS VALUES
# ===================

roi_analysis_type = Param( ## Essential parameter
    'roi_analysis_type',  
    title = "ROI Analysis Type",
    desc = """
    Defines the ROI analysis type run by RDR. 
    See the Technical Documentation for specifications and required inputs for each ROI analysis type.
    """,
    dtype = 'options', 
    options = ['BCA', 'Regret', 'Breakeven'], 
    short = 'rat')
param_list.append(roi_analysis_type)

dollar_year = Param( ## Essential parameter
    'dollar_year',  
    title = "Year for Dollar Units",
    desc = """
    Specifies the year in which all monetary benefit/cost units are input and reported. Costs include:
      \n1. vehicle operating costs, value of travel time, value of transit wait time, and transit fare in configuration file,
      \n2. project costs, redeployment costs (optional), and maintenance costs (optional) in project_info.csv input file,
      \n3. repair costs in repair costs table (default or user-defined),
      \n4. network link tolls in link tables (optional),
      \n5.  safety, noise, and emissions monetization values (default or user-defined).
    """,
    dtype = 'year', 
    value = 2024, 
    required = False, 
    short = 'dyr')
param_list.append(dollar_year)

discount_factor = Param(
    'discount_factor',  
    title = "Year-on-Year Discounting Factor",
    desc = """
    Defines the discounting factor used to convert metrics across entire period of analysis to year specified for dollar units.
      \nU.S. DOT recommended value is 0.07. Value should be entered as a decimal, not a percent.
    """,
    dtype = 'float', 
    value = 0.07, 
    required = False, 
    short = 'dfa')
param_list.append(discount_factor)

# co2_discount_factor = Param(
#     'co2_discount_factor',  
#     title = "Year-on-Year CO2 Discounting Factor",
#     desc = """
#     Defines the CO2-specific discounting factor used to convert metrics across entire period of analysis to year specified for dollar units.
#       \nU.S. DOT recommended value is 0.07. Value should be entered as a decimal, not a percent.
#     """,
#     dtype = 'float', 
#     value = 0.07, 
#     required = False, 
#     short = 'cfa')
# param_list.append(co2_discount_factor)

vehicle_occupancy_car = Param(
    'vehicle_occupancy_car',  
    title = "Vehicle Occupancy Rate - Car [persons/vehicle]",
    desc = """
    Defines average vehicle occupancy rates for passenger and transit vehicles used to convert passenger-miles traveled to vehicle-miles traveled and also to translate link capacities from vehicles / day / lane to persons / day for core model input.
      \nU.S. DOT recommended value for passenger vehicle is 1.52. Values for bus, light rail, and heavy rail are placeholders taken from the FTA 2024 National Transit Summaries and Trends report Exhibit 16.1 column "Average Occupancy (PMT/VRM)". User should provide their own values.
    """,
    dtype = 'float', 
    value = 1.52, 
    required = False, 
    short = 'occ')
param_list.append(vehicle_occupancy_car)

vehicle_occupancy_bus = Param( ## Conditional requirement
    'vehicle_occupancy_bus',  
    title = "Vehicle Occupancy Rate - Bus [persons/vehicle]",
    dtype = 'float', 
    value = 7.3, 
    required = False, 
    short = 'ocb')
param_list.append(vehicle_occupancy_bus) # required if params.calc_transit_metrics.value == 1

vehicle_occupancy_light_rail = Param( ## Conditional requirement
    'vehicle_occupancy_light_rail',  
    title = "Vehicle Occupancy Rate - Light Rail [persons/vehicle]",
    dtype = 'float', 
    value = 16, 
    required = False, 
    short = 'ocl') # required if params.calc_transit_metrics.value == 1
param_list.append(vehicle_occupancy_light_rail)

vehicle_occupancy_heavy_rail = Param( ## Conditional requirement
    'vehicle_occupancy_heavy_rail', 
    title = "Vehicle Occupancy Rate - Heavy Rail [persons/vehicle]",
    dtype = 'float',
    value = 16.8,
    required = False,
    short = 'ocr') # required if params.calc_transit_metrics.value == 1
param_list.append(vehicle_occupancy_heavy_rail)

veh_oper_cost_car = Param(
    'veh_oper_cost_car',  
    title = "Vehicle Operating Cost - Car [\$/vehicle-mile]",
    desc = """
    Defines the variable operating costs (e.g., gasoline, maintenance, tires, depreciation, transit operator time) for passenger and transit vehicles per mile driven.
      \nU.S. DOT recommended value in \$2024 for light duty vehicles is 0.56. Transit values in \$2024 are taken from the FTA 2024 National Transit Summaries and Trends report Exhibit 16.1, using "Operating Expenses (Millions)" divided by "VRM (Millions)", adjusted for inflation.
    """,
    dtype = 'float', value = 0.56, required = False, short = 'opc')
param_list.append(veh_oper_cost_car)

veh_oper_cost_bus = Param( ## Conditional requirement
    'veh_oper_cost_bus',  
    title = "Vehicle Operating Cost - Bus [\$/vehicle-mile]",
    dtype = 'float', 
    value = 17.08, 
    required = False, 
    short = 'opb') # Required if calc_transit_metrics = 1
param_list.append(veh_oper_cost_bus)

veh_oper_cost_light_rail = Param( ## Conditional requirement
    'veh_oper_cost_light_rail',  
    title = "Vehicle Operating Cost - Light Rail [\$/vehicle-mile]",
    dtype = 'float', 
    value = 30.65, 
    required = False, 
    short = 'opl') # Required if calc_transit_metrics = 1
param_list.append(veh_oper_cost_light_rail)

veh_oper_cost_heavy_rail = Param( ## Conditional requirement
    'veh_oper_cost_heavy_rail', 
    title = "Vehicle Operating Cost - Heavy Rail [\$/vehicle-mile]",
    dtype = 'float', 
    value = 18.32, 
    required = False, 
    short = 'opr') # Required if calc_transit_metrics = 1
param_list.append(veh_oper_cost_heavy_rail)

vot_per_hour = Param(
    'vot_per_hour',  
    title = "Value of Travel Time [\$/hour]",
    desc = """
    Defines the value of time used to convert link tolls in the network to travel time and to convert person-hours traveled to dollars.
      \nU.S. DOT recommended value in \$2024 is 21.80.
    """,
    dtype = 'float', 
    value = 21.80, 
    required = False, 
    short = 'vot')
param_list.append(vot_per_hour)

vot_wait_per_hour = Param( ## Conditional requirement
    'vot_wait_per_hour',  
    title = "Value of Wait Time [\$/hour]",
    desc = """
    Defines the value of time used to convert transit wait time on boarding links in the network in person-hours to dollars.
      \nU.S. DOT recommended value in $2024 is 40.20.
    """,
    dtype = 'float', 
    value = 40.20, 
    required = False, 
    short = 'vow') # Required if calc_transit_metrics == 1
param_list.append(vot_wait_per_hour)

transit_fare = Param( ## Conditional requirement
    'transit_fare', 
    title = "Transit Fare [\$/trip]",
    desc = """
    Defines the value of a transit trip used to convert trips lost to dollars.
    Value is a placeholder. User should provide their own value.
    """, 
    dtype = 'float', 
    value = 2.00, 
    short = 'far') # Required if calc_transit_metrics == 1
param_list.append(transit_fare)

maintenance = Param(
    'maintenance',  
    title = "Include Annual Maintenance Cost",
    desc = """
    Annual maintenance costs are defined in the project_info.csv input file and are applied every year.
      \nIf set to True, an 'Annual Maintenance Cost' column is required in the project info input file.
    """,
    dtype = 'options', 
    value = False, 
    required = False, 
    options = [True, False], 
    short = 'mai')
param_list.append(maintenance)

redeployment = Param(
    'redeployment',  
    title = "Include Redeployment Cost",
    desc = """
    Redeployment costs are defined in the project_info.csv input file and are applied every project lifespan AFTER the initial project deployment.
      \nIf set to True, a 'Redeployment Cost' column is required in the project info input file.
    """,
    dtype = 'options', 
    value = False, 
    required = False, 
    options = [True, False], 
    short = 'rdp')
param_list.append(redeployment)

safety_cost = Param(
    'safety_cost',  
    title = "Safety Cost - Car [\$/vehicle-mile]",
    desc = """
    Defines the safety external highway use costs per mile driven.
      \nU.S. DOT recommended per mile cost value divided by external share in \$2024 for light duty vehicles in urban location is 0.019 / 0.10 = 0.19.
      \nU.S. DOT recommended per mile cost value divided by external share in \$2024 for buses in urban location is 0.017 / 0.17 = 0.10.
    """,
    dtype = 'float', 
    value = 0.19, 
    required = False, 
    short = 'saf')
param_list.append(safety_cost)

safety_cost_bus = Param( ## Conditional requirement
    'safety_cost_bus', 
    title = "Safety Cost - Bus [$/vehicle-mile]",
    dtype = 'float', 
    value = 0.10, 
    required = False, 
    short = 'sab') # Required if calc_transit_metrics == 1
param_list.append(safety_cost_bus)

noise_cost = Param(
    'noise_cost', 
    title = "Noise Cost - Car [\$/vehicle-mile]",
    desc = """
    Defines the noise external highway use costs per mile driven.
    U.S. DOT recommended per mile value in \$2024 for light duty vehicles in urban location is 0.0021.
    U.S. DOT recommended per mile value in \$2024 for buses in urban location is 0.0465.
    """, 
    dtype = 'float', 
    value = 0.0021, 
    required = False, 
    short = 'nco')
param_list.append(noise_cost)

noise_cost_bus = Param( ## Conditional requirement
    'noise_cost_bus',  
    title = "Noise Cost - Bus [\$/vehicle-mile]",
    dtype = 'float', 
    value = 0.0465, 
    required = False, 
    short = 'ncb') # Required if calc_transit_metrics == 1
param_list.append(noise_cost_bus)

non_co2_cost = Param(
    'non_co2_cost',  
    title = "Non-CO2 Emissions Cost - Car [\$/vehicle-mile]",
    desc = """
    Defines the non-CO2 emissions external highway use costs per mile driven.
    U.S. DOT recommended per mile value in \$2024 for light duty vehicles in any location is 0.013.
    U.S. DOT recommended per mile value in \$2024 for buses in any location is 0.038.
    """,
    dtype = 'float', 
    value = 0.013, 
    required = False, 
    short = 'nra')
param_list.append(non_co2_cost)

non_co2_cost_bus = Param( ## Conditional requirement
    'non_co2_cost_bus', 
    title = "Non-CO2 Emissions Cost - Bus [\$/vehicle-mile]",
    dtype = 'float', 
    value = 0.038, 
    required = False, 
    short = 'nrb') # Required if calc_transit_metrics == 1
param_list.append(non_co2_cost_bus)

# co2_cost = Param(
#     'co2_cost', 
#     title = "CO2 Emissions Cost - Car [\$/vehicle-mile]",
#     desc = """
#     Defines the CO2 emissions external highway use costs per mile driven.
#     U.S. DOT recommended per mile value in \$2023 for light duty vehicles in urban location is 0.
#     U.S. DOT recommended per mile value in \$2023 for buses in urban location is 0.
#     """, 
#     dtype = 'float', 
#     value = 0, 
#     required = False, 
#     short = 'cra')
# param_list.append(co2_cost)

# co2_cost_bus = Param( ## Conditional requirement
#     'co2_cost_bus', 
#     title = "CO2 Emissions Cost - Bus [\$/vehicle-mile]",
#     dtype = 'float', 
#     value = 0, 
#     required = False, 
#     short = 'crb') # Required if calc_transit_metrics == 1
# param_list.append(co2_cost_bus)

crs = Param( ## Essential parameter
    'crs', 
    title = "Coordinate Reference System (CRS)",
    desc = """
    Defines the coordinate reference system (crs) of the TrueShape.csv WKT field
    Typically in the format of 'EPSG:XXXX' where XXXX is four digits
    Default is the WGS84 Geographic Coordinate System, which is EPSG:4326
    """, 
    value = 'EPSG:4326', 
    short = 'crs')
param_list.append(crs)

# ===================
# NON-CONFIG PARAMS
# ===================

# Non-config params are MultiParam, except those in 'Other inputs'
# MultiParam objects contain 'mini-params', which are Param objects that only exist for entry into a MultiParam
# MultiParam object groups are accessed through a 'primary param' Param object, whose multi-value (mval) is assigned to the list of MultiParam objects in a MultiParam group
# The primary param's multi-value should not be changed by the user; it should always be set to the corresponding list. Only the list itself should be changed by the user.
# Mini-params should not contain a short
# MultiParam objects may also require setting hidden params, such as when specifying the number of MultiParam objects to create for a given type
# MultiParam objects with a variable number of instances are instantiated at point of user entry rather than in this file

# Model Parameters (MOD)
model_tabs = []
# MOD primary param
model_params = Param('model_params', dtype = 'multi', mval = model_tabs, short = 'mop')
# param_list.append(model_params) # TODO: activate the model params once the in-app entry behavior is implemented
# MOD display params
mod_fpath = Param(
    'mod_fpath',
    title = "Model_Parameters.xlsx File Path",
    desc = """
    Defines the location of the Model_Parameters.xlsx file. 
      \nThis parameter should auto-populate if the input directory has been set and the Model_Parameters.xlsx is in its expected location.
      \nThe expected location is at the top level of the input directory (inputs/Model_Parameters.xlsx)
    """, 
    dtype = 'path',  
    short = 'modf') # Path to the ModelParameters.xlsx file
param_list.append(mod_fpath)
# MOD mini-params
mod_instruct = Param('mod_instruct', dtype = 'df') # Instructions tab (boilerplate, doesn't change)
model_tabs.append(mod_instruct)
mod_econscen = Param('mod_econscen', dtype = 'df') # EconomicScenarios tab
model_tabs.append(mod_econscen)
mod_elast = Param('mod_elast', dtype = 'df') # Elasticities tab
model_tabs.append(mod_elast)
mod_projgroups = Param('mod_projgroups', dtype = 'df') # ProjectGroups tab
model_tabs.append(mod_projgroups)
mod_haz = Param('mod_haz', dtype = 'df') # Hazards tab
model_tabs.append(mod_haz)
mod_recovstages = Param('mod_recovstages', dtype = 'df') # RecoveryStages tab
model_tabs.append(mod_recovstages)
mod_freqfact = Param('mod_freqfact', dtype = 'df') # FrequencyFactors tab
model_tabs.append(mod_freqfact)

# Hazards (HAZ)
hazard_list = []
haz_minis_list = []
# HAZ primary param
hazards = Param('hazards', dtype = 'multi', mval = hazard_list, short = 'haz')
# param_list.append(hazards) # TODO: activate hazards once in-app entry is implemented
# HAZ display params
haz_folder = Param(
    'haz_folder', 
    title = "Hazards Folder Path",
    desc = """
    Defines the location of the Hazards folder. 
      \nThis parameter should auto-populate if the input directory has been set and the Hazards folder is in its expected location.
      \nThe expected location is at the top level of the input directory (inputs/Hazards)
    """, 
    dtype = 'path', 
    short = 'hazf')
param_list.append(haz_folder)
# HAZ hidden params
haz_num = Param('haz_num', dtype = 'int', value = 1, short = 'hazn')  # Number of hazards
# HAZ mini-params
haz_name = Param('haz_name', dtype = 'str')
haz_minis_list.append(haz_name)
haz_fpath = Param('haz_fpath', dtype = 'path')
haz_minis_list.append(haz_fpath)
haz_df = Param('haz_df', dtype = 'df')
haz_minis_list.append(haz_df)

# Recovery stages
# See Recovery section above

# Event frequency factors (EFF)
eff_list = []
eff_minis_list = []
# EFF primary param
event_frequency_factors = Param('event_frequency_factors', dtype = 'multi', mval = eff_list, short = 'eff')
param_list.append(event_frequency_factors)
# EFF hidden params
eff_num = Param('eff_num', dtype = 'int', value = 1, short = 'effn')  # Number of EFFs
# EFF mini-params
eff_value = Param('eff_value', dtype = 'float')
eff_minis_list.append(eff_value)

# Economic futures (ECF)
ecf_list = []
ecf_minis_list = []
# ECF primary param
economic_futures = Param('economic_futures', dtype = 'multi', mval = ecf_list, short = 'ecf')
param_list.append(economic_futures)
# ECF hidden params
ecf_num = Param('ecf_num', dtype = 'int', value = 1, short = 'ecfn')  # Number of ECFs
# ECF mini-params
ecf_name = Param('ecf_name', dtype = 'str')
ecf_minis_list.append(ecf_name)
ecf_fpath = Param('ecf_fpath', dtype = 'str')
ecf_minis_list.append(ecf_fpath)

# Trip loss elasticities (TLE)
tle_list = []
tle_minis_list = []
# TLE primary param
trip_loss_elasticities = Param('trip_loss_elasticities', dtype = 'multi', mval = tle_list, short = 'tle')
param_list.append(trip_loss_elasticities)
# TLE hidden params
tle_num = Param('tle_num', dtype = 'int', value = 1, short = 'tlen')  # Number of TLEs
# TLE mini-params
tle_value = Param('tle_value', dtype = 'float')
tle_minis_list.append(tle_value)

# Resilience projects (REP)
rep_list = []
# TODO: use group_list for network link CSV files
group_list = []
rep_minis_list = []
# REP primary param
resilience_projects = Param('resilience_projects', dtype = 'multi', mval = rep_list, short = 'rep')
param_list.append(resilience_projects)
# REP hidden params
rep_num = Param('rep_num', dtype = 'int', value = 1, short = 'repn')  # Number of REPs
# REP mini-params
rep_name = Param('rep_name', dtype = 'str')
rep_minis_list.append(rep_name)
rep_group = Param('rep_group', dtype = 'str')
rep_minis_list.append(rep_group)

# Network links (derivative MultiParam formed for each ECF-REP_group pair) (NET)
netlink_list = []
net_minis_list = []
# NET primary param
network_links = Param('network_links', dtype = 'multi', mval = netlink_list, short = 'net')
param_list.append(network_links)
# NET display params
networks_folder = Param(
    'networks_folder',
    title = "Networks Folder Path",
    desc = """
    Defines the location of the Networks folder. 
      \nThis parameter should auto-populate if the input directory has been set and the Hazards folder is in its expected location.
      \nThe expected location is at the top level of the input directory (inputs/Networks)
    """, 
    dtype = 'path', 
    short = 'netf')
# NET mini-params
netlink_fpath = Param('netlink_fpath', dtype = 'path')
net_minis_list.append(netlink_fpath)

# Other input files (these are standard Param objects, not MultiParam)
net_node = Param('net_node', dtype = 'path', short = 'nwn')
param_list.append(net_node)

lookuptables_folder = Param(
    'lookuptables_folder', 
    title = "LookupTables Folder Path",
    desc = """
    Defines the location of the LookupTables folder, which contains project_info.csv, project_table.csv, and TrueShape.csv if it is provided. 
      \nThis parameter should auto-populate if the input directory has been set and the Hazards folder is in its expected location.
      \nThe expected location is at the top level of the input directory (inputs/LookupTables)
    """, 
    dtype = 'path', 
    short = 'ltf')
param_list.append(lookuptables_folder)

proj_table = Param('proj_table', dtype = 'path', short = 'prt')
param_list.append(proj_table)

proj_info = Param('proj_cost', dtype = 'path', short = 'pri')
param_list.append(proj_info)

# Matrices
aemaster_folder = Param(
    'aemaster_folder',
    title = "AEMaster Folder Path",
    desc = """
    Defines the location of the AEMaster folder, which contains the trip matrices. 
      \nThis parameter should auto-populate if the input directory has been set and the Hazards folder is in its expected location.
      \nThe expected location is at the top level of the input directory (inputs/AEMaster)
    """, 
    dtype = 'path', 
    short = 'aemf')
param_list.append(aemaster_folder)

# maintenance_column = Param('maintenance_column', dtype = 'str', value = 'Annual Maintenance Cost', short = 'mac') # Unused
# param_list.append(maintenance_column)

# redeployment_column = Param('redeployment_column', dtype = 'str', value = 'Redeployment Cost', short = 'rdc') # Unused
# param_list.append(redeployment_column)

base_year_file = Param('base_year_file', dtype = 'path', short = 'byf')
param_list.append(base_year_file)

# ===================
# BAT VALUES
# ===================

bat_location = Param(
    'bat_location', 
    title = "Batch File Location",
    desc = """
    Defines the location in which to save the associated batch file, which is the system instruction set that runs RDR. 
    """, 
    dtype = 'path', 
    value="C:/GitHub/RDR/", 
    short = 'bl')
param_list.append(bat_location)
     
python = Param(
    'python',
    title = "Python Installation Location",
    desc = """
    Defines the location of RDRenv Python installation. 
      \nThis parameter has a default value that works for most Python installations.
      \nIf it doesn't try: "C:/Users/%USERNAME%/AppData/Local/anaconda3/envs/RDRenv/python.exe"
    """, 
    dtype = 'path',
    short = 'py')
param_list.append(python)

rdr = Param(
    'rdr', 
    title = "RDR File",
    desc = """
    Defines the location of Run_RDR.py which is the main RDR script. 
      \nThis parameter has a default value that works for most RDR installations.
      \nChanging this value is not recommended.
    """, 
    dtype = 'path', 
    value="C:/GitHub/RDR/metamodel_py/Run_RDR.py", 
    short = 'rd')
param_list.append(rdr)

script = Param(
    'script',
    title = "Scripts Location",
    desc = """
    Defines the location of the Scripts folder. 
      \nThis parameter has a default value that populates after setting the {}.
      \nChanging this value is not recommended.
    """.format(python.title), 
    dtype = 'path',
    short = 'sc')
param_list.append(script)

bat_file = Param(
    'bat_file', 
    title = "Batch File",
    desc = """
    Defines the location of the associated batch file. 
      \nOnce a batch file is generated and associated with this save file, changing this value is not recommended.
    """, 
    dtype = 'path', 
    short = 'bat')
param_list.append(bat_file)

# ===================
# HIDDEN PARAMETERS
# ===================
# Hidden params are not appended to param_list (except seed) but can still be accessed using their short

hidden_list = []

seed = Param('seed', dtype = 'str', short = 'hseed')
hidden_list.append(seed)
param_list.append(seed)

save_folder = Param('save_folder', dtype = 'path', short = 'hsavd')
hidden_list.append(save_folder)

save_name = Param('save_name', dtype = 'str', value = 'myRDRsave', short = 'hsavn')
hidden_list.append(save_name)

save_file = Param(
    'save_file', 
    title = "Save File",
    desc = """
    Defines the location of the save file that is currently loaded.
    """,
    dtype = 'path', 
    short = 'hsavf'
    )
hidden_list.append(save_file)

current_param = Param('current_param', dtype = 'str', value = 'sequential', short = 'hcurr')
hidden_list.append(current_param)

previous_param = Param('previous_param', dtype = 'str', value = 'sequential', short = 'hprev')
hidden_list.append(previous_param)

dev_mode = Param('developer_mode', dtype = 'options', value = False, options = [True, False], short = 'hdevm')
hidden_list.append(dev_mode)

# ===================
# PARAM META
# ===================

names = [x.name for x in param_list]
dtypes = [x.dtype for x in param_list]
values = [x.value for x in param_list]
requireds = [x.required for x in param_list]
optionses = [x.options for x in param_list]
shorts = [x.short for x in param_list]
shortbackto = [x.short + 'backto' for x in param_list]

hidden_shorts = [x.short for x in hidden_list]

shorts_multi = [x.short for x in param_list if x.mval is not None]

if len(set(shorts)) != len(shorts):
    raise Exception('DEV ERROR: Parameter shortkey (short) must be unique for each parameter. {} non-unique shortkeys detected.'.format(len(shorts) - len(set(shorts))))

if len(set(names)) != len(names):
    raise Exception('DEV ERROR: Parameter name must be unique for each parameter. {} non-unique names detected.'.format(len(names) - len(set(names))))

short_dict = {names[x]:shorts[x] for x in list(range(0,len(names)))}
names_dict = {shorts[x]:names[x] for x in list(range(0,len(shorts)))}