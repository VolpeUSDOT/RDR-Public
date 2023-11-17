import arcpy
import os
import sys
import datetime
import csv
import configparser
from scipy import stats

# The following code takes a GIS-based raster data set representing exposure data (such as a flood depth grid data set
# and determines the maximum exposure value for each segment in a given transportation network within a user-specified
# tolerance. This is then converted to a level of disruption (defined as link availability) which feeds into the
# larger RDR Metamodel. There is a full set of documentation accompanying this tool.

# If RDR is being run on both a transit and a road network then the tool should be run separately for each subnetwork
# given that these networks usually come from different sources and may require different tool settings.
# Outputs can then be combined together.


def read_config_file_helper(config, section, key, required_or_optional):

    if not config.has_option(section, key):

        if required_or_optional.upper() == 'REQUIRED':
            raise Exception("CONFIG FILE ERROR: Can't find {} in section {}".format(key, section))

        return None

    else:
        val = config.get(section, key).strip().strip("'").strip('"')

        if val == '':
            return None
        else:
            return val


def read_config_file(cfg_file):

    cfg_dict = {}  # return value

    if not os.path.exists(cfg_file):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_file))

    cfg = configparser.RawConfigParser()
    cfg.read(cfg_file)

    # ===================
    # COMMON VALUES
    # ===================

    cfg_dict['input_exposure_grid'] = read_config_file_helper(cfg, 'common', 'input_exposure_grid', 'REQUIRED')
    if not arcpy.Exists(cfg_dict['input_exposure_grid']):
        raise Exception("CONFIG FILE ERROR: input input_exposure_grid grid {} "
                        "can't be found".format(cfg_dict['input_exposure_grid']))

    cfg_dict['input_network'] = read_config_file_helper(cfg, 'common', 'input_network', 'REQUIRED')
    if not arcpy.Exists(cfg_dict['input_network']):
        raise Exception("CONFIG FILE ERROR: input network {} "
                        "can't be found".format(cfg_dict['input_network']))

    cfg_dict['output_dir'] = read_config_file_helper(cfg, 'common', 'output_dir', 'REQUIRED')

    cfg_dict['run_name'] = read_config_file_helper(cfg, 'common', 'run_name', 'REQUIRED')

    cfg_dict['exposure_field'] = read_config_file_helper(cfg, 'common', 'exposure_field', 'REQUIRED')

    cfg_dict['fields_to_keep'] = read_config_file_helper(cfg, 'common', 'fields_to_keep', 'REQUIRED')

    cfg_dict['search_distance'] = read_config_file_helper(cfg, 'common', 'search_distance', 'REQUIRED')

    cfg_dict['comment_text'] = read_config_file_helper(cfg, 'common', 'comment_text', 'OPTIONAL')

    link_availability_approach = read_config_file_helper(cfg, 'common', 'link_availability_approach', 'OPTIONAL')
    # Set default to binary if this is not specified
    cfg_dict['link_availability_approach'] = 'binary'
    if link_availability_approach is not None:
        link_availability_approach = link_availability_approach.lower()
        if link_availability_approach not in ['binary', 'default_flood_exposure_function', 'manual',
                                              'beta_distribution_function']:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for link_availability_approach, should be 'binary', "
                "'default_flood_exposure_function', 'beta_distribution_function', or 'manual'".format(
                    link_availability_approach))
        else:
            cfg_dict['link_availability_approach'] = link_availability_approach

    # Set units of exposure if default flood exposure function is chosen
    if cfg_dict['link_availability_approach'] == 'default_flood_exposure_function':
        cfg_dict['exposure_unit'] = read_config_file_helper(cfg, 'common', 'exposure_unit', 'REQUIRED')
        if cfg_dict['exposure_unit'].lower() not in ['feet', 'foot', 'ft', 'yards', 'yard', 'm', 'meters']:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for exposure_unit, the default flood exposure function "
                "is currently only compatible with depths provided in 'feet', 'yards' or 'meters'".format(
                    cfg_dict['exposure_unit']))
    else:
        cfg_dict['exposure_unit'] = None

    if cfg_dict['link_availability_approach'] == 'manual':
        cfg_dict['link_availability_csv'] = read_config_file_helper(cfg, 'common', 'link_availability_csv', 'REQUIRED')
    else:
        cfg_dict['link_availability_csv'] = None

    if cfg_dict['link_availability_approach'] == 'beta_distribution_function':
        cfg_dict['alpha'] = float(read_config_file_helper(cfg, 'common', 'alpha', 'REQUIRED'))
        if cfg_dict['alpha'] <= 0:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['alpha'])) +
                            "alpha, should be number greater than 0")
        cfg_dict['beta'] = float(read_config_file_helper(cfg, 'common', 'beta', 'REQUIRED'))
        if cfg_dict['beta'] <= 0:
            raise Exception("CONFIG FILE ERROR: {} is an invalid value for ".format(str(cfg_dict['beta'])) +
                            "beta, should be number greater than 0")
        cfg_dict['lower_bound'] = float(read_config_file_helper(cfg, 'common', 'lower_bound', 'REQUIRED'))
        cfg_dict['upper_bound'] = float(read_config_file_helper(cfg, 'common', 'upper_bound', 'REQUIRED'))
        cfg_dict['beta_method'] = read_config_file_helper(cfg, 'common', 'beta_method', 'REQUIRED')
        if not cfg_dict['beta_method'] in ['lower cumulative', 'upper cumulative']:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for beta_method, should be 'lower cumulative' or "
                "'upper cumulative' (case sensitive)".format(cfg_dict['beta_method']))
    else:
        cfg_dict['alpha'] = None
        cfg_dict['beta'] = None
        cfg_dict['lower_bound'] = None
        cfg_dict['upper_bound'] = None
        cfg_dict['beta_method'] = None

    evacuation = read_config_file_helper(cfg, 'common', 'evacuation', 'OPTIONAL')
    cfg_dict['evacuation'] = False
    evacuation = evacuation.lower()
    if evacuation not in ['t', 'f', 'true', 'false', 'y', 'n', 'yes', 'no']:
        raise Exception("CONFIG FILE ERROR: {} is an invalid value for evacuation, should be true or false".format(
            evacuation))
    if evacuation in ['t', 'true', 'y', 'yes']:
        cfg_dict['evacuation'] = True

    if cfg_dict['evacuation'] is True:
        cfg_dict['evacuation_input'] = read_config_file_helper(cfg, 'common', 'evacuation_input', 'OPTIONAL')
        cfg_dict['evacuation_route_search_distance'] = read_config_file_helper(cfg, 'common',
                                                                               'evacuation_route_search_distance',
                                                                               'OPTIONAL')
    else:
        cfg_dict['evacuation_input'] = None
        cfg_dict['evacuation_route_search_distance'] = None

    emergency = read_config_file_helper(cfg, 'common', 'emergency', 'OPTIONAL')
    cfg_dict['emergency'] = False
    emergency = emergency.lower()
    if emergency not in ['t', 'f', 'true', 'false', 'y', 'n', 'yes', 'no']:
        raise Exception("CONFIG FILE ERROR: {} is an invalid value for emergency, should be true or false".format(
            emergency))
    if emergency in ['t', 'true', 'y', 'yes']:
        cfg_dict['emergency'] = True

    return cfg_dict


def exposure_grid_overlay(cfg):

    # SETUP
    # ---------------------------------------------------------------------------

    # Load config
    print('Loading configuration ...')
    input_exposure_grid = cfg['input_exposure_grid']
    input_network = cfg['input_network']
    output_dir = cfg['output_dir']
    run_name = cfg['run_name']
    exposure_field = cfg['exposure_field']
    fields_to_keep = cfg['fields_to_keep'].split(",")
    search_distance = cfg['search_distance']
    comment_text = cfg['comment_text']
    link_availability_approach = cfg['link_availability_approach']
    exposure_unit = cfg['exposure_unit']
    link_availability_csv = cfg['link_availability_csv']
    alpha = cfg['alpha']
    beta = cfg['beta']
    lower_bound = cfg['lower_bound']
    upper_bound = cfg['upper_bound']
    beta_method = cfg['beta_method']
    evacuation = cfg['evacuation']
    evacuation_input = cfg['evacuation_input']
    evacuation_route_search_distance = cfg['evacuation_route_search_distance']
    emergency = cfg['emergency']

    output_gdb = 'output_' + run_name + '.gdb'
    full_path_to_output_gdb = os.path.join(output_dir, output_gdb)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if arcpy.Exists(full_path_to_output_gdb):
        arcpy.Delete_management(full_path_to_output_gdb)
        print('Deleted existing ' + full_path_to_output_gdb)
    arcpy.CreateFileGDB_management(output_dir, output_gdb)

    arcpy.env.workspace = full_path_to_output_gdb

    print('{} link availability approach to be used'.format(link_availability_approach))

    # MAIN
    # ---------------------------------------------------------------------------

    # Extract raster cells that overlap the network
    print('Extracting exposure values that overlap network ...')
    arcpy.CheckOutExtension("Spatial")
    output_extract_by_mask = arcpy.sa.ExtractByMask(input_exposure_grid, input_network)
    output_extract_by_mask.save(run_name + "_exposure_grid_extract")
    arcpy.CheckInExtension("Spatial")

    # Export raster to point
    print('Converting raster to point ...')
    arcpy.RasterToPoint_conversion(run_name + "_exposure_grid_extract", os.path.join(
        full_path_to_output_gdb, run_name + "_exposure_grid_points"), exposure_field)

    # Setup field mapping so that maximum exposure at each segment is captured
    fms = arcpy.FieldMappings()

    for field in fields_to_keep:
        try:
            fm1 = arcpy.FieldMap()
            fm1.addInputField(input_network, field)
            fms.addFieldMap(fm1)
        except:
            raise Exception("Can't find field ({}) in the exposure dataset. Ensure that this field exists".format(field))

    fm2 = arcpy.FieldMap()
    fm2.addInputField(run_name + "_exposure_grid_points", "grid_code")
    fm2.mergeRule = 'Maximum'

    fms.addFieldMap(fm2)

    # Spatial join to network, selecting highest exposure value for each network segment
    print('Identifying maximum exposure value for each network segment ...')
    arcpy.SpatialJoin_analysis(input_network, run_name + "_exposure_grid_points",
                               run_name + "_network_with_exposure",
                               "JOIN_ONE_TO_ONE", "KEEP_ALL",
                               fms,
                               "WITHIN_A_DISTANCE_GEODESIC", search_distance)

    if evacuation is True:
        print('Flagging Evacuation Routes')

        arcpy.Buffer_analysis(evacuation_input, "evacuation_routes_buffered", evacuation_route_search_distance, "FULL",
                              "ROUND", "NONE", "", "GEODESIC")

        # Select by location in the buffer
        arcpy.AddField_management(run_name + "_network_with_exposure", "evacuation_route", "Short")
        arcpy.MakeFeatureLayer_management(run_name + "_network_with_exposure", "evacuation_layer")
        arcpy.SelectLayerByLocation_management("evacuation_layer", "COMPLETELY_WITHIN", "evacuation_routes_buffered")

        # Calculate field for emergency routes
        arcpy.CalculateField_management("evacuation_layer", "evacuation_route",
                                        '1', "PYTHON_9.3")
        arcpy.SelectLayerByAttribute_management("evacuation_layer", 'SWITCH_SELECTION')
        arcpy.CalculateField_management("evacuation_layer", "evacuation_route",
                                        '0', "PYTHON_9.3")

    # Add new field to store extent of exposure
    print('Calculating exposure levels ...')

    arcpy.AddField_management(run_name + "_network_with_exposure", "link_availability", "Float")
    arcpy.AddField_management(run_name + "_network_with_exposure", "comments", "Text")
    arcpy.CalculateField_management(run_name + "_network_with_exposure", "comments", '"' + comment_text + '"',
                                    "PYTHON_9.3")
    arcpy.MakeFeatureLayer_management(run_name + "_network_with_exposure", "network_with_exposure_lyr")

    # Convert NULLS to 0 first
    arcpy.SelectLayerByAttribute_management("network_with_exposure_lyr", "NEW_SELECTION", "grid_code IS NULL")
    arcpy.CalculateField_management("network_with_exposure_lyr", "grid_code", 0, "PYTHON_9.3")
    arcpy.SelectLayerByAttribute_management("network_with_exposure_lyr", "CLEAR_SELECTION")

    if link_availability_approach == 'binary':
        # 0 = full exposure/not traversible. 1 = no exposure/link fully available
        arcpy.SelectLayerByAttribute_management("network_with_exposure_lyr", "NEW_SELECTION", "grid_code > 0")
        arcpy.CalculateField_management("network_with_exposure_lyr", "link_availability", 0, "PYTHON_9.3")
        arcpy.SelectLayerByAttribute_management("network_with_exposure_lyr", "SWITCH_SELECTION")
        arcpy.CalculateField_management("network_with_exposure_lyr", "link_availability", 1, "PYTHON_9.3")

    if link_availability_approach == 'default_flood_exposure_function':
        # Use default flood exposure function which is based on a depth-damage function defined by Pregnolato et al.
        # in which the maximum safe vehicle speed reaches 0 at a depth of water of approximately 300 millimeters.
        # A linear relationship is assumed for link availability when water depths are between 0 and 300 millimeters
        with arcpy.da.UpdateCursor("network_with_exposure_lyr", ['grid_code', 'link_availability']) as ucursor:
            for row in ucursor:
                # Convert exposure units to millimeters
                if row[0] is not None:
                    if exposure_unit.lower() in ['feet', 'ft', 'foot']:
                        grid_code_mm = row[0] * 304.8
                    if exposure_unit.lower() in ['yards', 'yard']:
                        grid_code_mm = row[0] * 914.4
                    if exposure_unit.lower() in ['meters', 'm']:
                        grid_code_mm = row[0] * 1000
                else:
                    grid_code_mm = 0

                if grid_code_mm >= 300:
                    row[1] = 0
                elif 0 < grid_code_mm < 300:
                    row[1] = 1 - (grid_code_mm / 300)
                else:
                    row[1] = 1

                ucursor.updateRow(row)

    if link_availability_approach == 'manual':
        # Use manual approach where a user-defined csv lists the range of values and the link availability associated
        # with each range
        # Minimum (inclusive) and maximum (exclusive) value must be defined for each range.
        with arcpy.da.UpdateCursor("network_with_exposure_lyr", ['grid_code', 'link_availability']) as ucursor:
            for gis_row in ucursor:
                # Read through the csv
                # for line in csv
                with open(link_availability_csv, 'r') as rf:
                    line_num = 1
                    for line in rf:
                        if line_num > 1:
                            csv_row = line.rstrip('\n').split(',')
                            if gis_row[0] is not None:
                                if float(csv_row[0]) <= float(gis_row[0]) < float(csv_row[1]):
                                    gis_row[1] = csv_row[2]
                        line_num += 1
                # Set to fully available if the value is not in the table
                if gis_row[1] is None:
                    gis_row[1] = 1
                ucursor.updateRow(gis_row)

    if link_availability_approach == 'beta_distribution_function':
        with arcpy.da.UpdateCursor("network_with_exposure_lyr", ['grid_code', 'link_availability']) as ucursor:
            for row in ucursor:
                # Convert exposure units to millimeters
                if row[0] is not None:
                    if beta_method == 'lower cumulative':
                        if row[0] < lower_bound:
                            row[1] = 0
                        elif row[0] > upper_bound:
                            row[1] = 1

                        else:
                            row[1] = stats.beta.cdf(row[0], alpha, beta, loc=lower_bound,
                                                    scale=upper_bound-lower_bound)

                    elif beta_method == 'upper cumulative':
                        if row[0] < lower_bound:
                            row[1] = 1
                        elif row[0] > upper_bound:
                            row[1] = 0
                        else:
                            row[1] = 1-stats.beta.cdf(row[0], alpha, beta, loc=lower_bound,
                                                      scale=upper_bound-lower_bound)
                else:
                    row[1] = 1

                ucursor.updateRow(row)

    print('Finalizing outputs ...')

    # Rename grid_code back to the original exposure field provided in raster dataset.
    arcpy.AlterField_management(run_name + "_network_with_exposure", 'grid_code', exposure_field)

    if emergency is True:
        arcpy.AlterField_management(run_name + "_network_with_exposure", 'link_availability',
                                    'link_availability_emergency')

    txt_output_fields = fields_to_keep + ['link_availability', 'link_availability_emergency', 'evacuation_route',
                                          'comments']
    txt_output_fields.append(exposure_field)

    # Export to CSV file
    csv_out = os.path.join(output_dir, run_name + ".csv")
    fields = [x.name for x in arcpy.ListFields(run_name + "_network_with_exposure") if x.name in txt_output_fields]

    counter = 0

    if sys.version_info[0] < 3:
        with open(csv_out, "wb") as f:
            wr = csv.writer(f)
            wr.writerow(fields)
            with arcpy.da.SearchCursor(run_name + "_network_with_exposure", fields) as cursor:
                for row in cursor:
                    counter += 1
                    wr.writerow(row)

    else:
        with open(csv_out, "w", newline='') as f:
            wr = csv.writer(f)
            wr.writerow(fields)
            with arcpy.da.SearchCursor(run_name + "_network_with_exposure", fields) as cursor:
                for row in cursor:
                    counter += 1
                    wr.writerow(row)


def main():
    start_time = datetime.datetime.now()
    print('\nStart at ' + str(start_time))

    program_name = os.path.basename(__file__)

    if len(sys.argv) != 2:
        print('usage: ' + program_name + ' <full_path_to_config_file>')
        sys.exit()

    full_path_to_config_file = sys.argv[1]

    if not os.path.exists(full_path_to_config_file):
        print('ERROR: config file {} can''t be found!'.format(full_path_to_config_file))
        sys.exit()

    cfg = read_config_file(full_path_to_config_file)

    exposure_grid_overlay(cfg)

    end_time = datetime.datetime.now()
    total_run_time = end_time - start_time
    print("\nEnd at {}.  Total run time {}".format(end_time, total_run_time))


if __name__ == "__main__":
    main()
