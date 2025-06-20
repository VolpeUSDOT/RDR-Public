dtypes = ['str', 'path', 'year', 'options', 'int', 'float', 'multi']  # Add new dtypes as needed. Do not create dtypes that are used less than twice.

param_list = []  # param_list is simply the list of pointers to the Param objects in memory. Modification of the Param objects via the param_list is not advised.

class Param:
    def __init__(self, name:str, dtype:str = 'str', value = None, mval:list = None, required:bool = True, options:list = None, short:str = None):
        self.name = name
        self.dtype = dtype
        self.value = value
        self.mval = mval
        self.required = required
        self.options = options
        self.short = short
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

input_dir = Param('input_dir', dtype = 'path', short = 'in')
param_list.append(input_dir)

output_dir = Param('output_dir', dtype = 'path', short = 'ou')
param_list.append(output_dir)

run_id = Param('run_id', short = 'id')
param_list.append(run_id)

start_year = Param('start_year', dtype = 'year', short = 'sy')
param_list.append(start_year)

end_year = Param('end_year', dtype = 'year', short = 'ey')
param_list.append(end_year)

base_year = Param('base_year', dtype = 'year', short = 'by')
param_list.append(base_year)

future_year = Param('future_year', dtype = 'year', short = 'fy')
param_list.append(future_year)

# ===================
# METAMODEL VALUES
# ===================

metamodel_type = Param('metamodel_type', dtype = 'options', value = 'multitarget', required = False, 
                       options = ['base', 'interact', 'projgroupLM', 'multitarget', 'mixedeffects'],
                       short = 'met')
param_list.append(metamodel_type)

lhs_sample_target = Param('lhs_sample_target', dtype = 'int', short = 'lhs')
param_list.append(lhs_sample_target)

aeq_run_type = Param('aeq_run_type', dtype = 'options', value = 'RT', required = False, options = ['SP', 'RT'], short = 'art')
param_list.append(aeq_run_type)

run_minieq = Param('run_minieq', dtype = 'options', value = 0, required = False, options = [0, 1], short = 'rme')
param_list.append(run_minieq)

allow_centroid_flows = Param('allow_centroid_flows', dtype = 'options', value = 1, required = False, options = [0, 1], short = 'acf')
param_list.append(allow_centroid_flows)

calc_transit_metrics = Param('calc_transit_metrics', dtype = 'options', value = 0, required = False, options = [0, 1], short = 'ctm')
param_list.append(calc_transit_metrics)

aeq_max_iter = Param('aeq_max_iter', dtype = 'int', value = 100, required = False, short = 'ami')
param_list.append(aeq_max_iter)

aeq_rgap_target = Param('aeq_rgap_target', dtype = 'float', value = 0.01, required = False, short = 'agt')
param_list.append(aeq_rgap_target)

# ===================
# DISRUPTION VALUES
# ===================

link_availability_approach = Param('link_availability_approach', dtype = 'options', value = 'binary', required = False, 
                                   options = ['binary', 'default_flood_exposure_function', 'manual', 'facility_type_manual', 'beta_distribution_function'],
                                   short = 'laa')
param_list.append(link_availability_approach)

exposure_field = Param('exposure_field', dtype = 'str', value = 'Value', short = 'exf')
param_list.append(exposure_field)

link_availability_csv = Param('link_availability_csv', dtype = 'path', short = 'lap')  # Required if link_availability_approach == 'manual' or 'facility_type_manual'
param_list.append(link_availability_csv)

alpha = Param('alpha', dtype = 'float', short = 'alp')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(alpha)

beta = Param('beta', dtype = 'float', short = 'bet')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(beta)

lower_bound = Param('lower_bound', dtype = 'float', short = 'lob')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(lower_bound)

upper_bound = Param('upper_bound', dtype = 'float', short = 'upb')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(upper_bound)

beta_method = Param('beta_method', dtype = 'options', options = ['lower cumulative', 'upper cumulative'], short = 'bem')  # Required if link_availability_approach == 'beta_distribution_function'
param_list.append(beta_method)

highest_zone_number = Param('highest_zone_number', dtype = 'int', value = 0, required = False, short = 'zoc')
param_list.append(highest_zone_number)

resil_mitigation_approach = Param('resil_mitigation_approach', dtype = 'options', value = 'binary', required = False, options = ['binary', 'manual'],
                                  short = 'rma')
param_list.append(resil_mitigation_approach)

# ===================
# RECOVERY VALUES
# ===================

num_recovery_stages = Param('num_recovery_stages', dtype = 'int', short = 'nrs')
param_list.append(num_recovery_stages)

min_duration = Param('min_duration', dtype = 'float', short = 'mid')
param_list.append(min_duration)

max_duration = Param('max_duration', dtype = 'float', short = 'mad')
param_list.append(max_duration)

num_duration_cases = Param('num_duration_cases', dtype = 'int', short = 'ndc')
param_list.append(num_duration_cases)

hazard_recov_type = Param('hazard_recov_type', dtype = 'options', options = ['days', 'percent'], short = 'hrt')
param_list.append(hazard_recov_type)

hazard_recov_length = Param('hazard_recov_length', dtype = 'float', short = 'hrl')
param_list.append(hazard_recov_length)

hazard_recov_path_model = Param('hazard_recov_path_model', dtype = 'options', options = ['equal'], short = 'hrp')
param_list.append(hazard_recov_path_model)

exposure_damage_approach = Param('exposure_damage_approach', dtype = 'options', value = 'binary', required = False, options = ['binary', 'default_damage_table', 'manual'], 
                                 short = 'eda')
param_list.append(exposure_damage_approach)

exposure_unit = Param('exposure_unit', dtype = 'options', options = ['feet', 'foot', 'ft', 'yards', 'yard', 'm', 'meters'], short = 'exu')
param_list.append(exposure_unit)

exposure_damage_csv = Param('exposure_damage_csv', dtype = 'path', short = 'edp')
param_list.append(exposure_damage_csv)

repair_cost_approach = Param('repair_cost_approach', dtype = 'options', value = 'default', options = ['default', 'user-defined'], short = 'rca')
param_list.append(repair_cost_approach)

repair_network_type = Param('repair_network_type', dtype = 'options', 
                            options = ['Rural Flat', 'Rural Rolling', 'Rural Mountainous', 
                                       'Small Urban', 'Small Urbanized', 'Large Urbanized', 'Major Urbanized'],
                                        short = 'rnt')
param_list.append(repair_network_type)

repair_cost_csv = Param('repair_cost_csv', dtype = 'path', short = 'rcp')
param_list.append(repair_cost_csv)

repair_time_approach = Param('repair_time_approach', dtype = 'options', options = ['default', 'user-defined'], short = 'rta')
param_list.append(repair_time_approach)

repair_time_csv = Param('repair_time_csv', dtype = 'path', short = 'rtp')
param_list.append(repair_time_csv)

# ===================
# ANALYSIS VALUES
# ===================

roi_analysis_type = Param('roi_analysis_type', dtype = 'options', options = ['BCA', 'Regret', 'Breakeven'], short = 'rat')
param_list.append(roi_analysis_type)

dollar_year = Param('dollar_year', dtype = 'year', short = 'dyr')
param_list.append(dollar_year)

discount_factor = Param('discount_factor', dtype = 'float', value = 0.07, required = False, short = 'dfa')
param_list.append(discount_factor)

co2_discount_factor = Param('co2_discount_factor', dtype = 'float', value = 0.07, required = False, short = 'cfa')
param_list.append(co2_discount_factor)

vehicle_occupancy_car = Param('vehicle_occupancy_car', dtype = 'float', value = 1.52, required = False, short = 'occ')
param_list.append(vehicle_occupancy_car)

vehicle_occupancy_bus = Param('vehicle_occupancy_bus', dtype = 'float', value = 20, required = False, short = 'ocb')
param_list.append(vehicle_occupancy_bus)

vehicle_occupancy_light_rail = Param('vehicle_occupancy_light_rail', dtype = 'float', value = 140, required = False, short = 'ocl')
param_list.append(vehicle_occupancy_light_rail)

vehicle_occupancy_heavy_rail = Param('vehicle_occupancy_heavy_rail', dtype = 'float', value = 400, required = False, short = 'ocr')
param_list.append(vehicle_occupancy_heavy_rail)

veh_oper_cost_car = Param('veh_oper_cost_car', dtype = 'float', value = 0.56, required = False, short = 'opc')
param_list.append(veh_oper_cost_car)

veh_oper_cost_bus = Param('veh_oper_cost_bus', dtype = 'float', value = 1.37, required = False, short = 'opb')
param_list.append(veh_oper_cost_bus)

veh_oper_cost_light_rail = Param('veh_oper_cost_light_rail', dtype = 'float', value = 5.95, required = False, short = 'opl')
param_list.append(veh_oper_cost_light_rail)

veh_oper_cost_heavy_rail = Param('veh_oper_cost_heavy_rail', dtype = 'float', value = 4.17, required = False, short = 'opr')
param_list.append(veh_oper_cost_heavy_rail)

vot_per_hour = Param('vot_per_hour', dtype = 'float', value = 21.10, required = False, short = 'vot')
param_list.append(vot_per_hour)

vot_wait_per_hour = Param('vot_wait_per_hour', dtype = 'float', value = 38.80, required = False, short = 'vow')
param_list.append(vot_wait_per_hour)

transit_fare = Param('transit_fare', dtype = 'float', short = 'far')
param_list.append(transit_fare)

maintenance = Param('maintenance', dtype = 'options', value = False, required = False, options = [True, False], short = 'mai')
param_list.append(maintenance)

redeployment = Param('redeployment', dtype = 'options', value = False, required = False, options = [True, False], short = 'rdp')
param_list.append(redeployment)

safety_cost = Param('safety_cost', dtype = 'float', value = 0.18, required = False, short = 'saf')
param_list.append(safety_cost)

safety_cost_bus = Param('safety_cost_bus', dtype = 'float', value = 0.10, required = False, short = 'sab')
param_list.append(safety_cost_bus)

noise_cost = Param('noise_cost', dtype = 'float', value = 0.0020, required = False, short = 'nco')
param_list.append(noise_cost)

noise_cost_bus = Param('noise_cost_bus', dtype = 'float', value = 0.0453, required = False, short = 'ncb')
param_list.append(noise_cost_bus)

non_co2_cost = Param('non_co2_cost', dtype = 'float', value = 0.013, required = False, short = 'nra')
param_list.append(non_co2_cost)

non_co2_cost_bus = Param('non_co2_cost_bus', dtype = 'float', value = 0.037, required = False, short = 'nrb')
param_list.append(non_co2_cost_bus)

co2_cost = Param('co2_cost', dtype = 'float', value = 0, required = False, short = 'cra')
param_list.append(co2_cost)

co2_cost_bus = Param('co2_cost_bus', dtype = 'float', value = 0, required = False, short = 'crb')
param_list.append(co2_cost_bus)

crs = Param('crs', value = 'EPSG:4326', short = 'crs')
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

# Hazards (HAZ)
hazard_list = []
haz_minis_list = []
# HAZ primary param
hazards = Param('hazards', dtype = 'multi', mval = hazard_list, short = 'haz')
param_list.append(hazards)
# HAZ hidden params
haz_num = Param('haz_num', dtype = 'int', value = 1, short = 'hazn')  # Number of hazards
# HAZ mini-params
haz_name = Param('haz_name', dtype = 'str')
haz_minis_list.append(haz_name)
haz_fpath = Param('haz_fpath', dtype = 'path')
haz_minis_list.append(haz_fpath)
haz_dim1 = Param('haz_dim1', dtype = 'int')
haz_minis_list.append(haz_dim1)
haz_dim2 = Param('haz_dim2', dtype = 'int')
haz_minis_list.append(haz_dim2)
haz_prob = Param('haz_prob', dtype = 'float')
haz_minis_list.append(haz_prob)

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
# Netlink primary param
network_links = Param('network_links', dtype = 'multi', mval = netlink_list, short = 'net')
param_list.append(network_links)
# Netlink mini-params
netlink_fpath = Param('netlink_fpath', dtype = 'path')
net_minis_list.append(netlink_fpath)

# Other input files (these are standard Param objects, not MultiParam)
net_node = Param('net_node', dtype = 'path', short = 'nwn')
param_list.append(net_node)

proj_table = Param('proj_table', dtype = 'path', short = 'prt')
param_list.append(proj_table)

proj_info = Param('proj_cost', dtype = 'path', short = 'pri')
param_list.append(proj_info)

# maintenance_column = Param('maintenance_column', dtype = 'str', value = 'Annual Maintenance Cost', short = 'mac') # Unused
# param_list.append(maintenance_column)

# redeployment_column = Param('redeployment_column', dtype = 'str', value = 'Redeployment Cost', short = 'rdc') # Unused
# param_list.append(redeployment_column)

base_year_file = Param('base_year_file', dtype = 'path', short = 'byf')
param_list.append(base_year_file)

# ===================
# BAT VALUES
# ===================

bat_location = Param('bat_location', dtype = 'path', short = 'bl')
param_list.append(bat_location)
     
python = Param('python', dtype = 'path', short = 'py')
param_list.append(python)

rdr = Param('rdr', dtype = 'path', short = 'rd')
param_list.append(rdr)

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

save_file = Param('save_file', dtype = 'path', short = 'hsavf')
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