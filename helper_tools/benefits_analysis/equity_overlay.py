import os
import pandas as pd
import geopandas as gpd
import datetime
import sys
import urllib.request
import zipfile

# Import code from equity_config_reader.py for read_equity_config_file method
import equity_config_reader

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'metamodel_py'))

import rdr_setup
import rdr_supporting

def equity_overlay(cfg, logger):

    # Values from config file
    output_dir = cfg['benefits_analysis_dir']
    run_id = cfg['run_id']
    TAZ_col_name = cfg['TAZ_col_name']

    TAZ_source = cfg['TAZ_source']
    equity_source = cfg['equity_source']
    equity_feature = cfg['equity_feature']
    output_name = cfg['output_name']
    min_percentile_include = cfg['min_percentile_include']

    equity_crs = cfg['equity_crs']

    # Download and read in the CEJST data
    if equity_source.strip(' ').lower() == 'cejst':
        equity_shp_path = os.path.join(output_dir, 'CEJST', 'usa', 'usa.shp')
        if not os.path.exists(equity_shp_path):
            url = 'https://static-data-screeningtool.geoplatform.gov/data-versions/1.0/data/score/downloadable/1.0-shapefile-codebook.zip'
            equity_zip = os.path.join(output_dir, 'CEJST.zip')
            urllib.request.urlretrieve(url, equity_zip)

            CEJST_dir = os.path.join(output_dir, 'CEJST')
            with zipfile.ZipFile(equity_zip,'r') as cejst_zip:
                cejst_zip.extractall(CEJST_dir)

            usa_dir = os.path.join(CEJST_dir, 'usa')
            usa_zip = os.path.join(CEJST_dir, 'usa.zip')
            with zipfile.ZipFile(usa_zip,'r') as cejst_zip:
                cejst_zip.extractall(usa_dir)
    
    # Or set the equity source to the user-provided file
    else:
        equity_shp_path = equity_source
        
    # Search for shapefile
    equity_gdf = gpd.read_file(equity_shp_path)
    equity_gdf = equity_gdf.set_crs(equity_crs)
    equity_gdf = equity_gdf.to_crs('EPSG:4326')

    # Test for existence of TAZ_source
    if not os.path.exists(TAZ_source + '.shp'):
        logger.error('The TAZ source file {}.shp could not be found'.format(TAZ_source))
        raise Exception("TAZ FILE ERROR: {}.shp could not be found".format(TAZ_source))

    # Read in the TAZ shapefile
    TAZ_gdf = gpd.read_file(TAZ_source + '.shp')
    TAZ_gdf = TAZ_gdf.to_crs('EPSG:4326')

    # Rename columns from the user-specified TAZ column name
    TAZ_gdf = TAZ_gdf.rename(columns={TAZ_col_name: 'TAZ'})

    # Generate the TAZ-equity intersection shapes
    if not os.path.exists(os.path.join(output_dir, "TAZ_equity_intersect.gpkg")):
        logger.info('Intersecting {} with {}'.format(TAZ_source, equity_shp_path))
        TAZ_equity_intersect = TAZ_gdf.overlay(equity_gdf, how = 'intersection')
        TAZ_equity_intersect.to_file(os.path.join(output_dir, "TAZ_equity_intersect.gpkg"))
    else:
        TAZ_equity_intersect = gpd.read_file(os.path.join(output_dir, "TAZ_equity_intersect.gpkg"))

    # If a TAZ intersects with multiple equity emphasis areas, there may be multiple values for equity_feature
    # Merge these together using maximum or mean of equity_feature, excluding very small areas
    TAZ_equity_intersect = TAZ_equity_intersect.replace(-99999, 0)

    # Minimum area of TAZ-equity fragment to exclude from equity_feature calculation
    min_area = TAZ_equity_intersect.area.quantile(q = min_percentile_include)
    
    dups = TAZ_equity_intersect.groupby('TAZ').TAZ.count() > 1

    df_taz_dup = TAZ_equity_intersect.merge(dups, how='left', left_on='TAZ', right_index=True, suffixes=('', '_y'))

    # Filter out TAZ fragments which are below minimum size threshold but only if there are multiple fragments per TAZ
    df_taz_filter = df_taz_dup.loc[(df_taz_dup.area >= min_area) & (df_taz_dup['TAZ_y'] == True) | (df_taz_dup['TAZ_y'] == False)].copy()

    # Check whether equity variable is continuous
    is_continuous = df_taz_filter[equity_feature].nunique() >= 20

    logger.info('Equity feature {} is {} type. Continuous variable detected: {}'.format(equity_feature, df_taz_filter[equity_feature].dtype, is_continuous))

    if is_continuous:
        # If the equity feature is continuous, take the mean value
        df_out = df_taz_filter.groupby('TAZ')[equity_feature].mean()
    else:
        # If the equity feature is categorical, take the max value
        df_out = df_taz_filter.groupby('TAZ')[equity_feature].max()

    # Join back to TAZ data
    df_taz = TAZ_gdf

    df_taz_equity = df_taz.merge(df_out, how='left', left_on='TAZ', right_index=True)
    
    # Overwrite blank values that may have arisen from the merge just above, which can happen when the TAZ fragment filtering was too aggressive
    if any(pd.isna(df_taz_equity[equity_feature])):
        logger.info("Blank values are being overwritten in {}. Blank values can arise from a min_percentile_include parameter that is too high.".format(equity_feature))
        df_blanks = df_taz_equity.loc[pd.isna(df_taz_equity[equity_feature]),].copy()
        if is_continuous:
            df_out = pd.pivot_table(data = TAZ_equity_intersect, index = 'TAZ', aggfunc = {equity_feature : "mean"}).reset_index()

        else:
            df_out = pd.pivot_table(data = TAZ_equity_intersect, index = 'TAZ', aggfunc = {equity_feature : "max"}).reset_index()
            
        df_blanks[equity_feature] = df_blanks.reset_index().merge(df_out, how='left', on='TAZ', suffixes=('_x', ''), ).set_index('index')[equity_feature]
        df_taz_equity.loc[pd.isna(df_taz_equity[equity_feature]), equity_feature] = df_blanks[equity_feature]

    # Rename the 'TAZ' column back to whatever is specified by the user
    df_taz_equity = df_taz_equity.rename(columns={'TAZ' : TAZ_col_name})
    
    # Write out gpkg and csv files
    logger.info('Writing equity overlay geometric file as {} to directory {}'.format(output_name + '.gpkg', output_dir))
    df_taz_equity.to_file(os.path.join(output_dir, output_name + '.gpkg'))

    df_taz_equity = df_taz_equity.drop(columns = ['geometry'])

    logger.info('Writing equity overlay CSV file as {} to directory {}'.format(output_name + '.csv', output_dir))
    df_taz_equity.to_csv(os.path.join(output_dir, output_name + '.csv'), index=False)


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

    cfg = equity_config_reader.read_equity_config_file(full_path_to_config_file)

    output_dir = cfg['benefits_analysis_dir']

    # set up logging and report run start time
    # ----------------------------------------------------------------------------------------------
    logger = rdr_supporting.create_loggers(output_dir, 'equity_overlay', cfg)

    logger.info("=======================================================")
    logger.info("=============== EQUITY OVERLAY STARTING ===============")
    logger.info("=======================================================")

    equity_overlay(cfg, logger)

    end_time = datetime.datetime.now()
    total_run_time = end_time - start_time
    logger.info("Total run time: {}".format(total_run_time))


# ==============================================================================


if __name__ == "__main__":
    main()
