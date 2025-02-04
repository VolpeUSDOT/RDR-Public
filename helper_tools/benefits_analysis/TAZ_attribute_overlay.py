import os
import pandas as pd
import geopandas as gpd
import datetime
import sys
import urllib.request
import zipfile

# Import code from benefits_analysis_config_reader.py for read_benefits_analysis_config_file method
import benefits_analysis_config_reader

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'metamodel_py'))

import rdr_setup
import rdr_supporting

def attribute_overlay(cfg, logger):

    # Values from config file
    output_dir = cfg['benefits_analysis_dir']
    run_id = cfg['run_id']
    TAZ_col_name = cfg['TAZ_col_name']

    TAZ_source = cfg['TAZ_source']
    attribute_source = cfg['attribute_source']
    attribute_feature = cfg['attribute_feature']
    output_name = cfg['output_name']
    min_percentile_include = cfg['min_percentile_include']

    attribute_crs = cfg['attribute_crs']

    # Download and read in the census tract data
    if attribute_source.strip(' ').lower() == 'censuspoverty':
        tracts_path = os.path.join(output_dir, 'census_tracts', 'cb_2023_us_tract_500k.shp')
        if not os.path.exists(tracts_path):
            tract_zip = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir)),
                                     'config', 'taz_attribute_overlay', 'cb_2023_us_tract_500k.zip')

            tract_dir = os.path.join(output_dir, 'census_tracts')
            with zipfile.ZipFile(tract_zip, 'r') as zip_file:
                zip_file.extractall(tract_dir)

    # Or set the attribute source to the user-provided file
    else:
        tracts_path = attribute_source
        
    # Search for shapefile
    attribute_gdf = gpd.read_file(tracts_path)
    attribute_gdf = attribute_gdf.set_crs(attribute_crs)
    attribute_gdf = attribute_gdf.to_crs('EPSG:4269')

    # If applicable, get default poverty data to join with census tract geometry

    # https://www.census.gov/data/experimental-data-products/model-based-estimates-of-2021-persons-in-poverty.html
    # https://www2.census.gov/programs-surveys/demo/datasets/model-based-estimates/2021/Tract.csv
    # https://mtgis-portal.geo.census.gov/arcgis/apps/experiencebuilder/experience/?id=ad8ad0751e474f938fc98345462cdfbf&page=EDA-Census-Poverty-Status-Viewer&views=Modeled-Tract-Area-Poverty

    if attribute_source.strip(' ').lower() == 'censuspoverty':
        poverty_filepath = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir)),
                                        'config', 'taz_attribute_overlay', 'poverty.csv')
        poverty = pd.read_csv(poverty_filepath,
                              usecols=['state', 'county', 'tract', 'povrt'],
                              converters = {'state':str, 'county':str, 'tract':str})
        poverty['GEOID'] = poverty['state'] + poverty['county'] + poverty['tract']
        poverty = poverty[["GEOID", "povrt"]]
        poverty['poverty_percentage_bin'] = pd.Series("no data", index=poverty.index).case_when(
            [
                (poverty["povrt"] >= 20.00, 2),
                (poverty["povrt"] >= 10.00, 1),
                (poverty["povrt"] < 10.00, 0)
            ]
        )        
        attribute_gdf = attribute_gdf[['GEOID', 'geometry']]
        attribute_gdf = attribute_gdf.merge(poverty, on = 'GEOID')

    # Test for existence of TAZ_source
    if not os.path.exists(TAZ_source + '.shp'):
        logger.error('The TAZ source file {}.shp could not be found'.format(TAZ_source))
        raise Exception("TAZ FILE ERROR: {}.shp could not be found".format(TAZ_source))

    # Read in the TAZ shapefile
    TAZ_gdf = gpd.read_file(TAZ_source + '.shp')
    TAZ_gdf = TAZ_gdf.to_crs('EPSG:4269')

    # Rename columns from the user-specified TAZ column name
    TAZ_gdf = TAZ_gdf.rename(columns={TAZ_col_name: 'TAZ'})

    # Generate the TAZ-attribute intersection shapes
    if not os.path.exists(os.path.join(output_dir, "TAZ_attribute_intersect.gpkg")):
        logger.info('Intersecting {} with {}'.format(TAZ_source, tracts_path))
        TAZ_attribute_intersect = TAZ_gdf.overlay(attribute_gdf, how = 'intersection')
        TAZ_attribute_intersect.to_file(os.path.join(output_dir, "TAZ_attribute_intersect.gpkg"))
    else:
        TAZ_attribute_intersect = gpd.read_file(os.path.join(output_dir, "TAZ_attribute_intersect.gpkg"))

    # If a TAZ intersects with multiple attribute areas, there may be multiple values for attribute
    # Merge these together using maximum or mean of attribute, excluding very small areas
    TAZ_attribute_intersect = TAZ_attribute_intersect.replace(-99999, 0)

    # Minimum area of fragment to exclude from calculation
    min_area = TAZ_attribute_intersect.area.quantile(q = min_percentile_include)
    
    dups = TAZ_attribute_intersect.groupby('TAZ').TAZ.count() > 1

    df_taz_dup = TAZ_attribute_intersect.merge(dups, how='left', left_on='TAZ', right_index=True, suffixes=('', '_y'))

    # Filter out TAZ fragments which are below minimum size threshold but only if there are multiple fragments per TAZ
    df_taz_filter = df_taz_dup.loc[(df_taz_dup.area >= min_area) & (df_taz_dup['TAZ_y'] == True) | (df_taz_dup['TAZ_y'] == False)].copy()

    # Check whether attribute is continuous
    is_continuous = df_taz_filter[attribute_feature].nunique() >= 20

    logger.info('Attribute feature {} is {} type. Continuous variable detected: {}'.format(attribute_feature, df_taz_filter[attribute_feature].dtype, is_continuous))

    if is_continuous:
        # If the attribute is continuous, take the mean value
        df_out = df_taz_filter.groupby('TAZ')[attribute_feature].mean()
    else:
        # If the attribute is categorical, take the max value
        df_out = df_taz_filter.groupby('TAZ')[attribute_feature].max()

    # Join back to TAZ data
    df_taz = TAZ_gdf

    df_taz_attribute = df_taz.merge(df_out, how='left', left_on='TAZ', right_index=True)
    
    # Overwrite blank values that may have arisen from the merge just above, which can happen when the TAZ fragment filtering was too aggressive
    if any(pd.isna(df_taz_attribute[attribute_feature])):
        logger.info("Blank values are being overwritten in {}. Blank values can arise from a min_percentile_include parameter that is too high.".format(attribute_feature))
        df_blanks = df_taz_attribute.loc[pd.isna(df_taz_attribute[attribute_feature]),].copy()
        if is_continuous:
            df_out = pd.pivot_table(data = TAZ_attribute_intersect, index = 'TAZ', aggfunc = {attribute_feature : "mean"}).reset_index()

        else:
            df_out = pd.pivot_table(data = TAZ_attribute_intersect, index = 'TAZ', aggfunc = {attribute_feature : "max"}).reset_index()
            
        df_blanks[attribute_feature] = df_blanks.reset_index().merge(df_out, how='left', on='TAZ', suffixes=('_x', ''), ).set_index('index')[attribute_feature]
        df_taz_attribute.loc[pd.isna(df_taz_attribute[attribute_feature]), attribute_feature] = df_blanks[attribute_feature]

    # Rename the 'TAZ' column back to whatever is specified by the user
    df_taz_attribute = df_taz_attribute.rename(columns={'TAZ' : TAZ_col_name})
    
    # Write out gpkg and csv files
    logger.info('Writing TAZ attribute overlay geometric file as {} to directory {}'.format(output_name + '.gpkg', output_dir))
    df_taz_attribute.to_file(os.path.join(output_dir, output_name + '.gpkg'))

    df_taz_attribute = df_taz_attribute.drop(columns = ['geometry'])

    logger.info('Writing TAZ attribute overlay CSV file as {} to directory {}'.format(output_name + '.csv', output_dir))
    df_taz_attribute.to_csv(os.path.join(output_dir, output_name + '.csv'), index=False)


# ==============================================================================


def main():

    start_time = datetime.datetime.now()

    program_name = os.path.basename(__file__)

    if len(sys.argv) != 2:
        print("usage: " + program_name + " <full_path_to_config_file>")
        sys.exit()

    full_path_to_config_file = sys.argv[1]

    if not os.path.exists(full_path_to_config_file):
        print("ERROR: config file {} can't be found!".format(full_path_to_config_file))
        sys.exit()

    cfg = benefits_analysis_config_reader.read_benefits_analysis_config_file(full_path_to_config_file)

    output_dir = cfg['benefits_analysis_dir']

    # set up logging and report run start time
    # ----------------------------------------------------------------------------------------------
    logger = rdr_supporting.create_loggers(output_dir, 'TAZ_attribute_overlay', cfg)

    logger.info("=======================================================")
    logger.info("=========== TAZ ATTRIBUTE OVERLAY STARTING ============")
    logger.info("=======================================================")

    attribute_overlay(cfg, logger)

    end_time = datetime.datetime.now()
    total_run_time = end_time - start_time
    logger.info("Total run time: {}".format(total_run_time))


# ==============================================================================


if __name__ == "__main__":
    main()
