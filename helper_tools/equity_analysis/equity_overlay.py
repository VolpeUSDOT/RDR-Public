import arcpy
import os
import re
import pandas as pd
import datetime
import configparser
import logging
import datetime
import argparse
import traceback
import sys

import equity_config_reader

# Import modules from core code (two levels up) by setting path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'metamodel_py'))

import rdr_setup
import rdr_supporting


def getFieldNames(shp):
    fieldnames = [f.name for f in arcpy.ListFields(shp)]
    return fieldnames


def feature_class_to_pandas_data_frame(feature_class, field_list):
    """
    Load data into a Pandas Data Frame for subsequent analysis.
    :param feature_class: Input ArcGIS Feature Class.
    :param field_list: Fields for input.
    :return: Pandas DataFrame object.
    """
    return pd.DataFrame(
        arcpy.da.FeatureClassToNumPyArray(
            in_table=feature_class,
            field_names=field_list,
            skip_nulls=False,
            null_value=-99999
        )
    )


def equity_overlay(cfg, logger):

    # Values from config file
    output_dir = cfg['equity_analysis_dir']
    run_id = cfg['run_id']

    TAZ_source = cfg['TAZ_source']
    equity_source = cfg['equity_source']
    equity_feature = cfg['equity_feature']
    output_name = cfg['output_name']
    min_percentile_include = cfg['min_percentile_include']

    # Make ArcGIS geodatabase if one doesn't exist
    gdb = 'RDR_Equity_Overlay'
    full_path_gdb = os.path.join(output_dir, gdb + '.gdb')
    if(os.path.exists(full_path_gdb)):
        logger.info('Geodatabase {} has already been created'.format(gdb + '.gdb'))
        arcpy.env.workspace = full_path_gdb
    else:
        logger.info('Creating geodatabase {}'.format(gdb + '.gdb'))
        arcpy.management.CreateFileGDB(out_folder_path = output_dir,
                                       out_name = gdb)
        arcpy.env.workspace = full_path_gdb

    # Test for existence of TAZ_source
    if not os.path.exists(os.path.join(output_dir, TAZ_source + '.shp')):
        logger.error('The TAZ source file {}.shp is not found in the equity analysis directory {}'.format(TAZ_source, output_dir))
        raise Exception("TAZ FILE ERROR: {}.shp could not be found".format(TAZ_source))

    if not arcpy.Exists('TAZ_layer'):
        TAZ_layer = arcpy.management.MakeFeatureLayer(os.path.join(output_dir, TAZ_source + '.shp'), 'TAZ_layer')
    else:
        TAZ_layer = 'TAZ_layer'

    if not arcpy.Exists('equity_layer'):
        equity_layer = arcpy.management.MakeFeatureLayer(equity_source, 'equity_layer')
    else:
        equity_layer = 'equity_layer'

    if not arcpy.Exists('TAZ_equity_intersect'):
        logger.info('Intersecting {} with {}'.format(TAZ_source, equity_source))
        arcpy.analysis.Intersect([TAZ_layer, equity_layer], 'TAZ_equity_intersect', "ALL", None, "INPUT")

    # If a TAZ intersects with multiple Census tracts, there can be multiple values for equity_feature ('OverallDis' by default)
    # Merge these together using maximum of the equity_feature, excluding very small areas
    fieldnames = getFieldNames('TAZ_equity_intersect')
    fieldnames_select = fieldnames[3:len(fieldnames)]

    df = feature_class_to_pandas_data_frame('TAZ_equity_intersect', fieldnames_select).replace(-99999, 0)

    # Minimum area of TAZ fragment to exclude from maximum equity_feature calculation: bottom 5% of areas by default
    min_area = df.Shape_Area.quantile(q = min_percentile_include)
    dups = df.groupby('TAZ').TAZ.count() > 1

    df_taz_dup = df.merge(dups, how='left', left_on='TAZ', right_index=True, suffixes=('', '_y'))

    # Filter out TAZ fragments which are below minimum size threshold, but only if there are actually multiple fragments per TAZ
    df_taz_filter = df_taz_dup.loc[(df_taz_dup['Shape_Area'] >= min_area) & (df_taz_dup['TAZ_y'] == True) | (df_taz_dup['TAZ_y'] == False)].copy()

    # Get the maximum value of the equity_feature ('OverallDis' by default) for each TAZ
    df_out = df_taz_filter.groupby('TAZ')[equity_feature].max()

    # Join back to TAZ data
    fieldnames = getFieldNames('TAZ_layer')
    fieldnames_select = fieldnames[2:len(fieldnames)]
    df_taz = feature_class_to_pandas_data_frame('TAZ_layer', fieldnames_select)

    df_taz_equity = df_taz.merge(df_out, how='left', left_on='TAZ', right_index=True)

    logger.info('Writing equity overlay file as {} to directory {}'.format(output_name + '.csv', output_dir))

    df_taz_equity.to_csv(os.path.join(output_dir, output_name + '.csv'), index=False)


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

    output_dir = cfg['equity_analysis_dir']

    # set up logging and report run start time
    # ----------------------------------------------------------------------------------------------
    logger = rdr_supporting.create_loggers(output_dir, 'equity_overlay', cfg)

    logger.info("=========================================================================")
    logger.info("============== EQUITY OVERLAY STARTING ==================================")
    logger.info("=========================================================================")

    equity_overlay(cfg, logger)

    end_time = datetime.datetime.now()
    total_run_time = end_time - start_time
    logger.info("Total run time: {}".format(total_run_time))


if __name__ == "__main__":
    main()
