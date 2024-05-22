import arcpy
import os
import pandas as pd
import datetime
import sys

# Import code from equity_config_reader.py for read_equity_config_file method
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
    TAZ_col_name = cfg['TAZ_col_name']

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
    if not os.path.exists(TAZ_source + '.shp'):
        logger.error('The TAZ source file {}.shp could not be found'.format(TAZ_source))
        raise Exception("TAZ FILE ERROR: {}.shp could not be found".format(TAZ_source))

    if not arcpy.Exists('TAZ_layer'):
        TAZ_layer = arcpy.management.MakeFeatureLayer(TAZ_source + '.shp', 'TAZ_layer')
    else:
        TAZ_layer = 'TAZ_layer'

    if not arcpy.Exists('equity_layer'):
        equity_layer = arcpy.management.MakeFeatureLayer(equity_source, 'equity_layer')
    else:
        equity_layer = 'equity_layer'

    if not arcpy.Exists('TAZ_equity_intersect'):
        logger.info('Intersecting {} with {}'.format(TAZ_source, equity_source))
        arcpy.analysis.Intersect([TAZ_layer, equity_layer], 'TAZ_equity_intersect', "ALL", None, "INPUT")

    # If a TAZ intersects with multiple equity emphasis areas, there may be multiple values for equity_feature
    # Merge these together using maximum or mean of equity_feature, excluding very small areas
    fieldnames = getFieldNames('TAZ_equity_intersect')
    fieldnames_select = fieldnames[3:len(fieldnames)]

    df = feature_class_to_pandas_data_frame('TAZ_equity_intersect', fieldnames_select).replace(-99999, 0)

    # Rename columns from the user-specified TAZ column name
    df = df.rename(columns={TAZ_col_name: 'TAZ'})

    # Minimum area of TAZ-equity fragment to exclude from equity_feature calculation
    min_area = df.Shape_Area.quantile(q = min_percentile_include)
    dups = df.groupby('TAZ').TAZ.count() > 1

    df_taz_dup = df.merge(dups, how='left', left_on='TAZ', right_index=True, suffixes=('', '_y'))

    # Filter out TAZ fragments which are below minimum size threshold but only if there are multiple fragments per TAZ
    df_taz_filter = df_taz_dup.loc[(df_taz_dup['Shape_Area'] >= min_area) & (df_taz_dup['TAZ_y'] == True) | (df_taz_dup['TAZ_y'] == False)].copy()

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
    fieldnames = getFieldNames('TAZ_layer')
    fieldnames_select = fieldnames[2:len(fieldnames)]
    df_taz = feature_class_to_pandas_data_frame('TAZ_layer', fieldnames_select)

    df_taz = df_taz.rename(columns={TAZ_col_name: 'TAZ'})

    df_taz_equity = df_taz.merge(df_out, how='left', left_on='TAZ', right_index=True)

    # TODO: make sure this join is working as intended. Specifically right_on TAZ and left_index. Make sure it's actually pulling the right values in.
    # Overwrite blank values that may have arisen from the merge just above, which can happen when the TAZ fragment filtering was too aggressive
    if any(pd.isna(df_taz_equity[equity_feature])):
        logger.info("Blank values are being overwritten in {}. Blank values can arise from a min_percentile_include parameter that is too high.".format(equity_feature))
        if is_continuous:
            df_blanks = df_taz_equity.loc[pd.isna(df_taz_equity[equity_feature]),]
            df_out = df.groupby('TAZ').mean()
            df_blanks[equity_feature] = df_blanks.merge(df_out, how='left', right_on='TAZ', suffixes=('_x', ''), left_index=True)[equity_feature]
            df_taz_equity.loc[pd.isna(df_taz_equity[equity_feature]), equity_feature] = df_blanks[equity_feature]
        else:
            df_blanks = df_taz_equity.loc[pd.isna(df_taz_equity[equity_feature]),] 
            df_out = df.groupby('TAZ').max()
            df_blanks[equity_feature] = df_blanks.merge(df_out, how='left', right_on='TAZ', suffixes=('_x', ''), left_index=True)[equity_feature]
            df_taz_equity.loc[pd.isna(df_taz_equity[equity_feature]), equity_feature] = df_blanks[equity_feature]

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

    logger.info("=======================================================")
    logger.info("=============== EQUITY OVERLAY STARTING ===============")
    logger.info("=======================================================")

    equity_overlay(cfg, logger)

    end_time = datetime.datetime.now()
    total_run_time = end_time - start_time
    logger.info("Total run time: {}".format(total_run_time))


if __name__ == "__main__":
    main()
