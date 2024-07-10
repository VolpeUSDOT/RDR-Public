#!/usr/bin/env python
# coding: utf-8

# Read and summarize OMX trip table and skim file
import os
import numpy as np
import pandas as pd
import openmatrix as omx


def readOMX(filename, selectedMatrix, debug_mode):
    f = omx.open_file(filename)
    matrix_size = f.shape()
    if debug_mode:
        print('Shape: ', f.shape())
        print('Number of tables: ', len(f))
        print('Table names: ', f.list_matrices())
        print('Attributes: ', f.list_all_attributes())
    omx_df = f[selectedMatrix]
    if debug_mode:
        print('Sum of matrix elements: {:.9}'.format(np.sum(omx_df)))
        print('Percentiles: ', np.percentile(omx_df, (1, 10, 30, 50, 70, 90, 99)))
        print('Maximum: ', np.amax(omx_df))
    return omx_df, matrix_size, f


# Input arguments
fldr = 'C:/GitHub/RDR/helper_tools/format_demand/matrices'
demand_filename = 'demand_new.omx'
matrix_name = 'matrix'
skim_filename = 'skims.omx'

# Read the input OMX trip table
matrix_filename = os.path.join(fldr, demand_filename)
dem, matrix_size, trip_omx_file = readOMX(matrix_filename, matrix_name, True)

# Read the input OMX skim
skim_matrix_filename = os.path.join(fldr, skim_filename)
rtbt, rtbt_matrix_size, rtbf = readOMX(skim_matrix_filename, 'free_flow_time', False)
rtbd, rtbd_matrix_size, rtbf = readOMX(skim_matrix_filename, 'distance', False)
print('rtbt_matrix_size: ', rtbt_matrix_size)
print('time percentiles: ', np.percentile(rtbt, (1, 10, 30, 50, 70, 90, 99)))
print('rtbd_matrix_size: ', rtbd_matrix_size)
print('distance percentiles: ', np.percentile(rtbd, (1, 10, 30, 50, 70, 90, 99)))

rtb_cumtripcount = 0.0
rtb_cumtime = 0.0
rtb_cumdist = 0.0
counter = 0
zero_dem_count = 0
bad_skim_count = 0
largeval = 99999
# Routing base times and distances
for i in range(matrix_size[0]):
    tripcount = 0.0
    timecount = 0.0
    distcount = 0.0
    if i % 100 == 0:
        print('Row: ', i)
    for j in range(matrix_size[1]):
        if dem[i][j] < 0.01:
            zero_dem_count = zero_dem_count + 1
        else:
            if rtbt[i][j] < largeval:
                tripcount = tripcount + dem[i][j]
                timecount = timecount + dem[i][j]*rtbt[i][j]
                distcount = distcount + dem[i][j]*rtbd[i][j]
                counter = counter + 1
            else:
                bad_skim_count = bad_skim_count + 1
    rtb_cumtripcount = rtb_cumtripcount + tripcount
    rtb_cumtime = rtb_cumtime + timecount
    rtb_cumdist = rtb_cumdist + distcount
print('Counter: ', counter, ', zero_dem: ', zero_dem_count, ', bad_skim: ', bad_skim_count)
print('Trips: ', rtb_cumtripcount, ', time: ', rtb_cumtime, ', distance: ', rtb_cumdist)

trip_omx_file.close()
rtbf.close()

