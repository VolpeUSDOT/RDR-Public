# dictionary of conversion factors between common units
# key is a tuple of the from unit and the to unit
DISTANCE_CONVERSIONS = {
    ("kilometer", "meter"): 1000.0,
    ("meter", "kilometer"): 0.001,
    ("centimeter", "meter"): 0.01,
    ("meter", "millimeter"): 1000.0,
    ("millimeter", "meter"): 0.001,
    ("mile", "foot"): 5280.0,
    ("foot", "mile"): 1 / 5280.0,
    ("yard", "foot"): 3.0,
    ("foot", "yard"): 1 / 3.0,
    ("foot", "inch"): 12.0,
    ("inch", "foot"): 1 / 12.0,
    ("meter", "foot"): 3.280839895,
    ("foot", "meter"): 0.3048,
    ("mile", "meter"): 1609.344,
    ("meter", "mile"): 0.000621371192,
    ("kilometer", "mile"): 0.621371192,
    ("mile", "kilometer"): 1.609344,
    ("inch", "centimeter"): 2.54,
    ("centimeter", "inch"): 1 / 2.54,
    ("survey_foot", "meter"): 1200 / 3937,
    ("meter", "survey_foot"): 3937 / 1200,
    ("foot", "survey_foot"): 0.999998,
    ("survey_foot", "foot"): 1.000002,
    ("foot", "milimeter"): 304.8,
    ("meter", "milimeter"): 100.0,
    ("yard", "milimeter"): 914.4,
}


def create_connection_string_raster(exposure_grid_path):
    """Creates a GDA compatible connection string for loading in raster data
    Args:
        exposure_grid_path (Path): input full path to raster layer (if it is a geodatabase use the full path (e.g. geodatabasename.gdb / rasterlayername))
    Returns:
        Retuns a string or None. If returns None it could not build the path.
    """
    from pathlib import Path

    if type(exposure_grid_path) is str:
        exposure_grid_path = Path(exposure_grid_path)
    extension = exposure_grid_path.suffix
    if extension == "":
        extension = exposure_grid_path.parent.suffix
        if extension == ".gdb":
            connection_string = (
                f'OpenFileGDB:"{exposure_grid_path.parent}":{exposure_grid_path.name}'
            )
            return connection_string
        elif extension == ".gpkg":
            connection_string = (
                f'GPKG:"{exposure_grid_path.parent}":{exposure_grid_path.name}'
            )
            return connection_string
        else:
            return None
    elif extension.lower() in (".tif", ".tiff", ".jpg", ".jpeg", "asc"):
        return str(exposure_grid_path)
    else:
        return None


def get_vector_inputs(vector_path):
    """Creates a GDAl compatible connection string for the vector input
    Args:
        vector_path (Path): full path to the vector layer ((if it is a geodatabase use the full path (e.g. geodatabasename.gdb / vectorlayername)))
    Returns:
        list: if the path leads to a geodatabse or geopackage there are two items in the list. The first index is the gdb / gpkg path, the second item is the layer name.
        if the path leads to a shapefile, there is one item in the list.
    """
    from pathlib import Path

    if type(vector_path) is str:
        vector_path = Path(vector_path)
    extension = vector_path.suffix
    if extension == "":
        extension = vector_path.parent.suffix
        if extension == ".gdb" or extension == ".gpkg":
            return [str(vector_path.parent), vector_path.name]
        else:
            return None
    elif extension.lower() in (".shp"):
        return [str(vector_path)]
    else:
        return None


def separate_distance_unit(input_string: str):
    """
    Parses input string to separate the number from the units.
    Args:
        input_string (str): the input string formatted Number Units (e.g. 100 meters, 2 Miles)
    Returns:
        tuple: First item is the number, second item is the unit. If both are None the text was not formatted correctly.
    """
    import re

    pattern = re.compile(r"^(\d+(?:\.\d+)?)(?:\s+(.+))?$")
    match = pattern.match(input_string)
    if match:
        # Extract groups by index
        number = float(match.group(1))
        unit = match.group(2) if match.group(2) else None
        return (number, unit)
    return (None, None)


def standardize_units(unit_name:str):
    """
    Converts abbreviations and different spellings to a standard unit. E.g. feet to foot, yd to yard
    Args:
        unit_name (str): unit name
    Returns:
        standard unit name that corresponds to the DISTANCE_CONVERSIONS dictionary.
    """
    unique_units = []
    for x, y in DISTANCE_CONVERSIONS.keys():
        unique_units.append(x)
        unique_units.append(y)
    unique_units = list(set(unique_units))
    unique_units.remove("foot")
    unique_units.remove("meter")
    unit_name = unit_name.replace(" ", "_").lower()
    for uu in unique_units:
        if uu in unit_name:
            return uu
    if "feet" in unit_name or "foot" in unit_name or "ft" == unit_name[:2]:
        return "foot"
    if "meter" in unit_name or "m" == unit_name[:1]:
        return "meter"
    if "in" == unit_name[:2]:
        return "inch"
    if "yd" == unit_name[:2]:
        return "yard"
    if "cm" == unit_name[:2]:
        return "centimeter"
    if "mm" == unit_name[:2]:
        return "milimeter"
    return None

