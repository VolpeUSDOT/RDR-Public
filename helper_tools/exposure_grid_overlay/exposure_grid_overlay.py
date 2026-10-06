import configparser
import datetime
import gc
import logging
import math
import os
import sys
from datetime import datetime

import numpy as np
import shapely
from scipy import stats
import warnings

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "metamodel_py"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "common"))
# Make sure the gdal dll are available
if "CONDA_PREFIX" in os.environ:
    conda_path = os.environ["CONDA_PREFIX"]

    if sys.platform == "win32":
        gdal_path = os.path.join(conda_path, "Library", "share", "gdal")
        proj_path = os.path.join(conda_path, "Library", "share", "proj")
    else:
        gdal_path = os.path.join(conda_path, "share", "gdal")
        proj_path = os.path.join(conda_path, "share", "proj")

    # Inject paths into the environment if they exist
    if os.path.exists(gdal_path):
        os.environ["GDAL_DATA"] = gdal_path
    if os.path.exists(proj_path):
        os.environ["PROJ_DATA"] = proj_path
        os.environ["PROJ_LIB"] = proj_path  # Fallback for older pyproj versions

import geopandas as gpd
import pandas as pd
import rioxarray
import dask
import shared_tools

# The following code takes a GIS-based raster data set representing exposure data (such as a flood depth grid data set
# and determines the maximum exposure value for each segment in a given transportation network within a user-specified
# tolerance. This is then converted to a level of disruption (defined as link availability) which feeds into the
# larger RDR Metamodel. There is a full set of documentation accompanying this tool.

# If RDR is being run on both a transit and a road network then the tool should be run separately for each subnetwork
# given that these networks usually come from different sources and may require different tool settings.
# Outputs can then be combined together.


# ==================================================================


# Note that this function is duplicated from the create_loggers in rdr_supporting due to the
# different environment and slightly different logging setup required.
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
    logging.addLevelName(logging.RESULT, "RESULT")

    logging.CONFIG = 19
    logging.addLevelName(logging.CONFIG, "CONFIG")

    logging.RUNTIME = 11
    logging.addLevelName(logging.RUNTIME, "RUNTIME")

    logging.DETAILED_DEBUG = 5
    logging.addLevelName(logging.DETAILED_DEBUG, "DETAILED_DEBUG")

    logger = logging.getLogger("log")
    logger.setLevel(logging.DEBUG)

    logger.result = lambda msg, *args: logger._log(logging.RESULT, msg, args)
    logger.config = lambda msg, *args: logger._log(logging.CONFIG, msg, args)
    logger.runtime = lambda msg, *args: logger._log(logging.RUNTIME, msg, args)
    logger.detailed_debug = lambda msg, *args: logger._log(
        logging.DETAILED_DEBUG, msg, args
    )

    # FILE LOG
    # ------------------------------------------------------------------------------
    logFileName = (
        task
        + "_log_"
        + cfg["run_name"]
        + "_"
        + datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
        + ".log"
    )
    file_log = logging.FileHandler(os.path.join(loggingLocation, logFileName), mode="a")
    file_log.setLevel(logging.DEBUG)

    file_log_format = logging.Formatter(
        "%(asctime)s.%(msecs).03d %(levelname)-8s %(message)s", datefmt="%m-%d %H:%M:%S"
    )
    file_log.setFormatter(file_log_format)

    # DOS WINDOW LOG
    # ------------------------------------------------------------------------------
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    # To show more detail on screen, i.e. for GitHub workflow, use DEBUG level
    # console.setLevel(logging.DEBUG)

    console_log_format = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(message)s", datefmt="%m-%d %H:%M:%S"
    )
    console.setFormatter(console_log_format)

    # ADD THE HANDLERS
    # ----------------
    logger.addHandler(file_log)
    logger.addHandler(console)

    return logger


# ==================================================================


def read_config_file_helper(config, section, key, required_or_optional):

    if not config.has_option(section, key):
        if required_or_optional.upper() == "REQUIRED":
            raise Exception(
                "CONFIG FILE ERROR: Can't find {} in section {}".format(key, section)
            )

        return None

    else:
        val = config.get(section, key).strip().strip("'").strip('"')

        if val == "":
            return None
        else:
            return val


# ==================================================================


def read_config_file(cfg_file, root_dir=None):

    cfg_dict = {}  # return value

    if not os.path.exists(cfg_file):
        raise Exception("CONFIG FILE ERROR: {} could not be found".format(cfg_file))

    cfg = configparser.RawConfigParser()
    cfg.read(cfg_file)

    # ===================
    # COMMON VALUES
    # ===================

    cfg_dict["input_exposure_grid"] = read_config_file_helper(
        cfg, "common", "input_exposure_grid", "REQUIRED"
    )
    if cfg_dict["input_exposure_grid"] is None:
        raise Exception("CONFIG FILE ERROR: Input exposure grid must be defined")

    cfg_dict["input_network"] = read_config_file_helper(
        cfg, "common", "input_network", "REQUIRED"
    )
    if cfg_dict["input_network"] is None:
        raise Exception("CONFIG FILE ERROR: Input network must be defined")
    cfg_dict["output_dir"] = read_config_file_helper(
        cfg, "common", "output_dir", "REQUIRED"
    )

    cfg_dict["run_name"] = read_config_file_helper(
        cfg, "common", "run_name", "REQUIRED"
    )

    cfg_dict["exposure_field"] = read_config_file_helper(
        cfg, "common", "exposure_field", "REQUIRED"
    )

    cfg_dict["fields_link_id"] = read_config_file_helper(
        cfg, "common", "fields_link_id", "REQUIRED"
    )

    cfg_dict["fields_from_node_id"] = read_config_file_helper(
        cfg, "common", "fields_from_node_id", "REQUIRED"
    )

    cfg_dict["fields_to_node_id"] = read_config_file_helper(
        cfg, "common", "fields_to_node_id", "REQUIRED"
    )

    cfg_dict["fields_additional_to_keep"] = read_config_file_helper(
        cfg, "common", "fields_additional_to_keep", "REQUIRED"
    )

    cfg_dict["search_distance"] = read_config_file_helper(
        cfg, "common", "search_distance", "REQUIRED"
    )

    cfg_dict["comment_text"] = read_config_file_helper(
        cfg, "common", "comment_text", "OPTIONAL"
    )

    link_availability_approach = read_config_file_helper(
        cfg, "common", "link_availability_approach", "OPTIONAL"
    )
    # Set default to binary if this is not specified
    cfg_dict["link_availability_approach"] = "binary"
    if link_availability_approach is not None:
        link_availability_approach = link_availability_approach.lower()
        if link_availability_approach not in [
            "binary",
            "default_flood_exposure_function",
            "manual",
            "facility_type_manual",
            "beta_distribution_function",
        ]:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for link_availability_approach, should be 'binary', "
                "'default_flood_exposure_function', 'manual', 'facility_type_manual', "
                "or 'beta_distribution_function'".format(link_availability_approach)
            )
        else:
            cfg_dict["link_availability_approach"] = link_availability_approach

    # Set units of exposure if default flood exposure function is chosen
    if cfg_dict["link_availability_approach"] == "default_flood_exposure_function":
        cfg_dict["exposure_unit"] = read_config_file_helper(
            cfg, "common", "exposure_unit", "REQUIRED"
        )
        if cfg_dict["exposure_unit"].lower() not in [
            "feet",
            "foot",
            "ft",
            "yards",
            "yard",
            "m",
            "meters",
        ]:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for exposure_unit, the default flood exposure function "
                "is currently only compatible with depths provided in 'feet', 'yards', or 'meters'".format(
                    cfg_dict["exposure_unit"]
                )
            )
    else:
        cfg_dict["exposure_unit"] = None

    if (
        cfg_dict["link_availability_approach"] == "manual"
        or cfg_dict["link_availability_approach"] == "facility_type_manual"
    ):
        cfg_dict["link_availability_csv"] = read_config_file_helper(
            cfg, "common", "link_availability_csv", "REQUIRED"
        )
        if cfg_dict["link_availability_csv"] is None:
            raise Exception(
                "CONFIG FILE ERROR: Input link availability csv path must be defined"
            )
        if not os.path.exists(cfg_dict["link_availability_csv"]):
            raise Exception(
                "CONFIG FILE ERROR: Input link availability csv {} "
                "can't be found".format(cfg_dict["link_availability_csv"])
            )
    else:
        cfg_dict["link_availability_csv"] = None

    if cfg_dict["link_availability_approach"] == "beta_distribution_function":
        cfg_dict["alpha"] = float(
            read_config_file_helper(cfg, "common", "alpha", "REQUIRED")
        )
        if cfg_dict["alpha"] <= 0:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for ".format(
                    str(cfg_dict["alpha"])
                )
                + "alpha, should be number greater than 0"
            )
        cfg_dict["beta"] = float(
            read_config_file_helper(cfg, "common", "beta", "REQUIRED")
        )
        if cfg_dict["beta"] <= 0:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for ".format(
                    str(cfg_dict["beta"])
                )
                + "beta, should be number greater than 0"
            )
        cfg_dict["lower_bound"] = float(
            read_config_file_helper(cfg, "common", "lower_bound", "REQUIRED")
        )
        cfg_dict["upper_bound"] = float(
            read_config_file_helper(cfg, "common", "upper_bound", "REQUIRED")
        )
        cfg_dict["beta_method"] = read_config_file_helper(
            cfg, "common", "beta_method", "REQUIRED"
        )
        if cfg_dict["beta_method"] not in ["lower cumulative", "upper cumulative"]:
            raise Exception(
                "CONFIG FILE ERROR: {} is an invalid value for beta_method, should be 'lower cumulative' or "
                "'upper cumulative' (case sensitive)".format(cfg_dict["beta_method"])
            )
    else:
        cfg_dict["alpha"] = None
        cfg_dict["beta"] = None
        cfg_dict["lower_bound"] = None
        cfg_dict["upper_bound"] = None
        cfg_dict["beta_method"] = None

    evacuation = read_config_file_helper(cfg, "common", "evacuation", "OPTIONAL")
    cfg_dict["evacuation"] = False
    evacuation = evacuation.lower()
    if evacuation not in ["t", "f", "true", "false", "y", "n", "yes", "no"]:
        raise Exception(
            "CONFIG FILE ERROR: {} is an invalid value for evacuation, should be true or false".format(
                evacuation
            )
        )
    if evacuation in ["t", "true", "y", "yes"]:
        cfg_dict["evacuation"] = True

    if cfg_dict["evacuation"] is True:
        cfg_dict["evacuation_input"] = read_config_file_helper(
            cfg, "common", "evacuation_input", "OPTIONAL"
        )
        cfg_dict["evacuation_route_search_distance"] = read_config_file_helper(
            cfg, "common", "evacuation_route_search_distance", "OPTIONAL"
        )
        inputs = ["input_network", "input_exposure_grid", "output_dir", "evacuation_input"]
    else:
        cfg_dict["evacuation_input"] = None
        cfg_dict["evacuation_route_search_distance"] = None
        inputs = ["input_network", "input_exposure_grid", "output_dir"]

    emergency = read_config_file_helper(cfg, "common", "emergency", "OPTIONAL")
    cfg_dict["emergency"] = False
    emergency = emergency.lower()
    if emergency not in ["t", "f", "true", "false", "y", "n", "yes", "no"]:
        raise Exception(
            "CONFIG FILE ERROR: {} is an invalid value for emergency, should be true or false".format(
                emergency
            )
        )
    if emergency in ["t", "true", "y", "yes"]:
        cfg_dict["emergency"] = True
    
    for x in inputs:
        if x in cfg_dict:
            if cfg_dict[x][0]=="." and root_dir:
                cfg_dict[x] = cfg_dict[x].replace(".\\", root_dir)

    return cfg_dict


# ==================================================================


def exposure_grid_overlay(cfg, logger):

    # SETUP
    # ---------------------------------------------------------------------------

    # Load config
    logger.info("Loading configuration ...")
    input_exposure_grid = cfg["input_exposure_grid"]
    input_network = cfg["input_network"]
    output_dir = cfg["output_dir"]
    run_name = cfg["run_name"]
    exposure_field = cfg["exposure_field"]
    fields_additional_to_keep = cfg["fields_additional_to_keep"].split(",")
    fields_link_id = cfg["fields_link_id"]
    fields_from_node_id = cfg["fields_from_node_id"]
    fields_to_node_id = cfg["fields_to_node_id"]

    search_distance = cfg["search_distance"]
    comment_text = cfg["comment_text"]
    link_availability_approach = cfg["link_availability_approach"]
    exposure_unit = cfg["exposure_unit"]
    link_availability_csv = cfg["link_availability_csv"]
    alpha = cfg["alpha"]
    beta = cfg["beta"]
    lower_bound = cfg["lower_bound"]
    upper_bound = cfg["upper_bound"]
    beta_method = cfg["beta_method"]
    evacuation = cfg["evacuation"]
    evacuation_input = cfg["evacuation_input"]
    evacuation_route_search_distance = cfg["evacuation_route_search_distance"]
    emergency = cfg["emergency"]

    output_gpkg = "output_" + run_name + ".gpkg"
    full_path_to_output_gpkg = os.path.join(output_dir, output_gpkg)
    output_shp = "output_" + run_name + ".shp"
    full_path_to_output_shp = os.path.join(output_dir, output_shp)

    logger.info(
        "{} link availability approach to be used".format(link_availability_approach)
    )

    logger.info(
        f"Output directory: {output_dir}"
    )

    # MAIN
    # ---------------------------------------------------------------------------
    # convert the input_network path to a version compatible with gdal and geopandas
    input_paths = shared_tools.get_vector_inputs(input_network)
    if input_paths is None:
        logger.info("Unsupported vector format for input network...")
        raise Exception("Unsupported vector format for input network")

    if os.path.exists(output_dir) is False:
        os.mkdir(output_dir)

    # get the gdal connection string for the input_exposure_grid
    connection_string = shared_tools.create_connection_string_raster(input_exposure_grid)
    if connection_string is None:
        logger.info("Unsupported raster format for exposure grid....")
        raise Exception("Unsupported raster format for exposure grid.")

    # Extract raster cells that overlap the network
    logger.info("Extracting exposure values that overlap network ...")

    # load the raster for the crs info
    rds = rioxarray.open_rasterio(
        connection_string, 
        chunks={"x": 2048, "y": 2048}, 
        masked=True
    )
    rds_crs = rds.rio.crs

    # load the network feature class
    gdf = None
    if len(input_paths) == 2:
        gdf = gpd.read_file(input_paths[0], layer=input_paths[1])
    elif len(input_paths) == 1:
        gdf = gpd.read_file(input_paths[0])
    else:
        raise Exception("Unsupported vector format for input network.")

    gdf.to_crs(rds_crs, inplace=True)

    if gdf is None:
        raise Exception("Unknown error occured.")

    # Assuming connection_string, gdf, logger, search_distance, run_name, full_path_to_output_gpkg exist...
    
    # Assume there is one band to the raster grid
    band1 = rds.sel(band=1)

    # get the spatial index and the x and y coordinates of the raster grid
    spatial_index = gdf.sindex
    x_coords = band1.x.values
    y_coords = band1.y.values

    # get the raster values for each coordinate
    y_chunks = band1.chunks[0]
    x_chunks = band1.chunks[1]

    y_edges = np.insert(np.cumsum(y_chunks), 0, 0)
    x_edges = np.insert(np.cumsum(x_chunks), 0, 0)

    res_x, res_y = band1.rio.resolution()
    pad_x, pad_y = abs(res_x), abs(res_y)

    collected_xs = []
    collected_ys = []
    collected_vals = []

    logger.info(
            "Streaming in raster data..."
        )

    # Looping over the raster in chunks decreases the load time and memory usage
    for i in range(len(y_chunks)):
        for j in range(len(x_chunks)):
            y_start, y_end = y_edges[i], y_edges[i+1]
            x_start, x_end = x_edges[j], x_edges[j+1]
            
            # Pull 1D coordinates for just this tile
            chunk_x = x_coords[x_start:x_end]
            chunk_y = y_coords[y_start:y_end]
            
            # Create a bounding box for the current tile
            minx, maxx = chunk_x.min() - pad_x, chunk_x.max() + pad_x
            miny, maxy = chunk_y.min() - pad_y, chunk_y.max() + pad_y
            tile_box = shapely.box(minx, miny, maxx, maxy)
            
            # Quick spatial index check: Does this tile touch any polylines?
            possible_line_indices = spatial_index.query(tile_box, predicate="intersects")
            if len(possible_line_indices) == 0:
                continue  # Skip reading or allocating anything for this tile!
                
            # Extract the specific lines intersecting this local tile
            intersecting_lines = gdf.iloc[possible_line_indices].geometry

            chunk_lazy = band1.isel(y=slice(y_start, y_end), x=slice(x_start, x_end))
            chunk_computed = chunk_lazy.compute()

            clipped_tile = chunk_computed.rio.clip(
                intersecting_lines, 
                crs=band1.rio.crs, 
                all_touched=True, 
                drop=False
            )

            tile_vals = clipped_tile.values
            valid_y, valid_x = np.where(~np.isnan(tile_vals))
            
            if len(valid_y) > 0:
                collected_xs.append(chunk_x[valid_x])
                collected_ys.append(chunk_y[valid_y])
                collected_vals.append(tile_vals[valid_y, valid_x])

    if collected_xs:
        xs = np.concatenate(collected_xs)
        ys = np.concatenate(collected_ys)
        valid_values = np.concatenate(collected_vals)
    else:
        xs, ys, valid_values = np.array([]), np.array([]), np.array([])

    # convert the raster grid to point coordinates in a geodataframe
    gdf_r = gpd.GeoDataFrame(
        {
            "grid_code": valid_values,
            "x_coord": xs,
            "y_coord": ys
        },
        geometry=gpd.points_from_xy(xs, ys),
        crs=gdf.crs
    )

    # if the coordinate reference system is geographic, convert to UTM so we can use euclidean distances
    if rds_crs.is_geographic is True:
        logger.info(
            "Projecting to UTM for analysis."
        )
        utm_crs = gdf.estimate_utm_crs()
        gdf.to_crs(utm_crs, inplace=True)
        gdf_r.to_crs(utm_crs, inplace=True)

    # get the number and units for the search_distance
    search_distance_value, search_distance_unit = shared_tools.separate_distance_unit(search_distance)

    # get the conversion factor for the search distance to utm meters
    search_distance_unit_to_gdf_units = (shared_tools.standardize_units(search_distance_unit), shared_tools.standardize_units(gdf.crs.axis_info[0].unit_name))
    # if they're the same units just use a factor of 1
    factor = 1 if len(set(search_distance_unit_to_gdf_units)) <= 1 else shared_tools.DISTANCE_CONVERSIONS[search_distance_unit_to_gdf_units]
    # search distance in utm units
    max_distance = search_distance_value * factor

    if None in search_distance_unit_to_gdf_units:
        logger.info(
            "Unable to deterimine the search_distance units. Are you using a projected coordinate reference system?"
        )
        raise Exception("Unable to deterimine the search_distance units.")
    
    logger.info("Identifying maximum exposure value for each network segment ...")
    # spatial join the raster data to the network data
    joined_to_grid = gdf_r.sjoin(
        gdf, how="inner", predicate="dwithin", distance=max_distance
    )

    # get the max grid value per network segment
    grid_max = (
        joined_to_grid.groupby(  # [~(pd.isnull(joined_to_grid["link_id"]))]
            ["index_right", "link_id"]
        )["grid_code"]
        .max()
        .reset_index()
    )

    grid_max.set_index(grid_max["index_right"], inplace=True)
    # get the grid_code exposure value joined back to the network layer
    gdf = gdf.join(grid_max["grid_code"])

    if evacuation is True:
        logger.info("Flagging Evacuation Routes")
        # follows a similar process as above
        # get the path, get the standard units and conversion factors for the evacuation search distance
        # join to the network if they are in an evacuation zone
        evacuation_paths = shared_tools.get_vector_inputs(evacuation_input)
        gdf_evac = None
        if len(evacuation_paths) == 2:
            gdf_evac = gpd.read_file(evacuation_paths[0], layer=evacuation_paths[1])
        elif len(input_paths) == 1:
            gdf_evac = gpd.read_file(evacuation_paths[0])
        else:
            logger.info("Unsupported vector format for evacuation input.")
            raise Exception("Unsupported vector format for evacuation input.")
        gdf_evac.to_crs(gdf_r.crs, inplace=True)
        e_search_distance_value, e_search_distance_unit = shared_tools.separate_distance_unit(
            evacuation_route_search_distance
        )
        e_search_distance_unit_to_gdf_units = (
            shared_tools.standardize_units(e_search_distance_unit),
            shared_tools.standardize_units(gdf_evac.crs.axis_info[0].unit_name),
        )
        e_factor = 1 if len(set(e_search_distance_unit_to_gdf_units)) <= 1 else shared_tools.DISTANCE_CONVERSIONS[e_search_distance_unit_to_gdf_units]
        
        gdf_evac["geometry"] = gdf_evac.buffer(e_search_distance_value * e_factor)
        joined = gpd.sjoin(gdf, gdf_evac, predicate="within", how="left")
        joined["evacuation_route"] = 0
        joined.loc[~(pd.isnull(joined["index_right"])), "evacuation_route"] = 1
        gdf = gdf.join(joined["evacuation_route"])

    # Add new field to store extent of exposure
    logger.info("Calculating exposure levels ...")
    gdf["comments"] = comment_text
    gdf.loc[pd.isnull(gdf["grid_code"]), "grid_code"] = 0.0

    if link_availability_approach == "binary":
        # 0 = full exposure/not traversible. 1 = no exposure/link fully available
        gdf["link_availability"] = 1
        gdf["link_availability"] = np.where(
            gdf["grid_code"] > 0, 0, gdf["link_availability"]
        )

    if link_availability_approach == "default_flood_exposure_function":
        # Use default flood exposure function which is based on a depth-damage function defined by Pregnolato et al.
        # in which the maximum safe vehicle speed reaches 0 at a depth of water of approximately 300 millimeters.
        # A linear relationship is assumed for link availability when water depths are between 0 and 300 millimeters
        exposure_unit = shared_tools.standardize_units(exposure_unit)
        if exposure_unit is None:
            raise Exception("Unable to determine exposure units.")

        exposure_unit_factor = 1 if len(set((exposure_unit, "milimeter"))) <= 1 else shared_tools.DISTANCE_CONVERSIONS[(exposure_unit, "milimeter")]
        gdf["grid_code_mm"] = gdf["grid_code"] * exposure_unit_factor
        gdf["link_availability"] = 0
        gdf["link_availability"] = np.where(gdf["grid_code_mm"] >= 300, 0, 1)
        gdf["link_availability"] = np.where(
            (gdf["grid_code_mm"] > 0) & (gdf["grid_code_mm"] < 300),
            1 - (gdf["grid_code_mm"] / 300),
            gdf["link_availability"],
        )

    if link_availability_approach == "manual":
        # Use manual approach where a user-defined CSV lists the range of values and the link availability associated
        # with each range
        # Minimum (inclusive) and maximum (exclusive) value must be defined for each range.
        link_availability_df = None
        if link_availability_csv.endswith(".csv"):
            link_availability_df = pd.read_csv(link_availability_csv)
        elif link_availability_csv.endswith(".xlsx"):
            link_availability_df = pd.read_excel(link_availability_csv)

        if link_availability_df is not None:
            if "min_inclusive" in link_availability_df.columns:
                gdf["link_availability"] = 1
                for _, row in link_availability_df.iterrows():
                    gdf["link_availability"] = np.where(
                        (gdf["grid_code"] >= row["min_incluisive"])
                        & (gdf["grid_code"] < row["max_excluisive"]),
                        row["link_availability"],
                        gdf["link_availability"],
                    )

    if link_availability_approach == "facility_type_manual":
        # Use manual approach where a user-defined CSV lists the range of values and the link availability associated
        # with each range for every facility type
        # Minimum (inclusive) and maximum (exclusive) value must be defined for each range.

        link_availability_df = None
        if link_availability_csv.endswith(".csv"):
            link_availability_df = pd.read_csv(link_availability_csv)
        elif link_availability_csv.endswith(".xlsx"):
            link_availability_df = pd.read_excel(link_availability_csv)

        if link_availability_df is not None:
            if "min_inclusive" in link_availability_df.columns:
                gdf["link_availability"] = None
                for _, row in link_availability_df.iterrows():
                    gdf.loc[
                        gdf["facility_type"] == row["facility_type"],
                        "link_availability",
                    ] = np.where(
                        (gdf["grid_code"] >= row["min_incluisive"])
                        & (gdf["grid_code"] < row["max_excluisive"]),
                        row["link_availability"],
                        gdf["link_availability"],
                    )

                gdf.loc[pd.isnull(gdf["link_availability"]), "link_availability"] = 1

    if link_availability_approach == "beta_distribution_function":
        if beta_method == "lower cumulative":
            gdf["link_availability"] = None
            gdf.loc[
                (gdf["grid_code"] >= lower_bound) & (gdf["grid_code"] <= upper_bound),
                "link_availability",
            ] = stats.beta.cdf(
                gdf[
                    (gdf["grid_code"] >= lower_bound)
                    & (gdf["grid_code"] <= upper_bound)
                ]["grid_code"],
                alpha,
                beta,
                loc=lower_bound,
                scale=upper_bound - lower_bound,
            )
            gdf["link_availability"] = np.where(
                gdf["grid_code"] < lower_bound, 0, gdf["link_availability"]
            )
            gdf["link_availability"] = np.where(
                gdf["grid_code"] > upper_bound, 1, gdf["link_availability"]
            )
            gdf.loc[pd.isnull(gdf["link_availability"]), "link_availability"] = 1
        elif beta_method == "upper cumulative":
            gdf["link_availability"] = None
            gdf.loc[
                (gdf["grid_code"] >= lower_bound) & (gdf["grid_code"] <= upper_bound),
                "link_availability",
            ] = stats.beta.cdf(
                gdf[
                    (gdf["grid_code"] >= lower_bound)
                    & (gdf["grid_code"] <= upper_bound)
                ]["grid_code"],
                alpha,
                beta,
                loc=lower_bound,
                scale=upper_bound - lower_bound,
            )
            gdf["link_availability"] = np.where(
                gdf["grid_code"] < lower_bound, 1, gdf["link_availability"]
            )
            gdf["link_availability"] = np.where(
                gdf["grid_code"] > upper_bound, 0, gdf["link_availability"]
            )
            gdf.loc[pd.isnull(gdf["link_availability"]), "link_availability"] = 1

    logger.info("Finalizing outputs ...")
    rename_columns = {
        "grid_code": exposure_field,
        fields_from_node_id: "from_node_id",
        fields_to_node_id: "to_node_id",
        fields_link_id: "link_id",
    }

    gdf.rename(columns=rename_columns, inplace=True)

    if emergency is True:
        gdf.rename(
            columns={"link_availability": "link_availability_emergency"}, inplace=True
        )

    txt_output_fields = [
        "from_node_id",
        "to_node_id",
        "link_id",
        exposure_field,
        "link_availability",
        "link_availability_emergency",
        "evacuation_route",
        "comments",
    ] + fields_additional_to_keep

    # Export to CSV file
    csv_out = os.path.join(output_dir, run_name + ".csv")
    fields = [x for x in gdf.columns if x in txt_output_fields]
    gdf[exposure_field] = gdf[exposure_field].astype("float64")
    gdf_r["grid_code"] = gdf_r["grid_code"].astype("float64")
    pd.DataFrame(gdf[fields]).to_csv(csv_out, index=False)

    warnings.filterwarnings("ignore", message=".*Column names longer than.*")
    warnings.filterwarnings("ignore", message=".*Normalized/laundered field name.*")
    gdf = gdf.reset_index(drop=True)

    # Writing to both a geopackage and a shapefile
    # sometimes the geopackage doesn't load correctly into ArcGIS Pro
    gdf.to_file(
        full_path_to_output_gpkg,
        layer=run_name + "_network_with_exposure",
        driver="GPKG",
        index=True
    )

    output_shp = "output_network_with_exposure_" + run_name + ".shp"
    full_path_to_output_shp = os.path.join(output_dir, output_shp)
    gdf.to_file(
        full_path_to_output_shp, 
        driver="ESRI Shapefile"
    )

    gdf_r = gdf_r.reset_index(drop=True)
    gdf_r.to_file(
        full_path_to_output_gpkg,
        layer=run_name + "_network_with_exposure_grid_points",
        driver="GPKG",
        index=True
    )
    output_shp = "output_network_with_exposure_grid_points_" + run_name + ".shp"
    full_path_to_output_shp = os.path.join(output_dir, output_shp)
    gdf.to_file(
        full_path_to_output_shp, 
        driver="ESRI Shapefile"
    )


# ==================================================================


def main():

    start_time = datetime.now()

    program_name = os.path.basename(__file__)

    if len(sys.argv) not in (2, 3):
        print("usage: " + program_name + " <full_path_to_config_file>" )
        sys.exit()

    full_path_to_config_file = sys.argv[1]
    try:
        root_dir = sys.argv[2]
    except:
        root_dir = None

    if not os.path.exists(full_path_to_config_file):
        print("ERROR: config file {} cant be found!".format(full_path_to_config_file))
        sys.exit()

    cfg = read_config_file(full_path_to_config_file, root_dir)

    # set up logging and report run start time
    # ----------------------------------------------------------------------------------------------
    output_dir = cfg["output_dir"]   
    logger = create_loggers(output_dir, "exposure_overlay", cfg)

    logger.info("=======================================================")
    logger.info("=============== EXPOSURE GRID OVERLAY STARTING ===============")
    logger.info("=======================================================")

    exposure_grid_overlay(cfg, logger)

    end_time = datetime.now()
    total_run_time = end_time - start_time
    logger.info("\nEnd at {}.  Total run time {}".format(end_time, total_run_time))


# ==================================================================

if __name__ == "__main__":
    main()
