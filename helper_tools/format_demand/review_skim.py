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
        print('Sum of matrix elements: {:.9}'.format(float(np.sum(omx_df))))
        print('Percentiles (1, 10, 30, 50, 70, 90, 99): ', np.percentile(omx_df, (1, 10, 30, 50, 70, 90, 99)))
        print('Maximum: ', np.amax(omx_df))
    return omx_df, matrix_size, f


# ==============================================================================


def main():
    # Input arguments
    print("Provide trip table OMX file path to review (drag and drop is fine here):")
    matrix_filename = ""
    while not os.path.exists(matrix_filename):
        matrix_filename = input('----------------------> ').strip('\"')
        print("USER INPUT ----------------->:  {}".format(matrix_filename))
        if not os.path.exists(matrix_filename):
            print("Path is not valid. Please enter a valid OMX file path.")

    f = omx.open_file(matrix_filename)
    print("Matrix names in OMX file are: {}. Provide name of matrix to review:".format(f.list_matrices()))
    matrix_name = ""
    while matrix_name == "":
        matrix_name = input('----------------------> ').strip('\"')
        print("USER INPUT ----------------->:  {}".format(matrix_name))
        if matrix_name == "exit":
            break
        elif matrix_name not in f.list_matrices():
            print("Matrix name is not valid. Please enter a valid matrix name. Matrix names in OMX file are: {}. Enter 'exit' to exit.".format(f.list_matrices()))
            matrix_name = ""
    f.close()

    print("Provide skims OMX file path to review (drag and drop is fine here). Skims file should include matrices for free_flow_time and distance:")
    skim_matrix_filename = ""
    while not os.path.exists(skim_matrix_filename):
        skim_matrix_filename = input('----------------------> ').strip('\"')
        print("USER INPUT ----------------->:  {}".format(skim_matrix_filename))
        if not os.path.exists(skim_matrix_filename):
            print("Path is not valid. Please enter a valid OMX file path.")

    if matrix_name != "exit":
        # Read the input OMX trip table
        dem, matrix_size, trip_omx_file = readOMX(matrix_filename, matrix_name, True)

        # Read the input OMX skim
        rtbt, rtbt_matrix_size, rtbf1 = readOMX(skim_matrix_filename, 'free_flow_time', False)
        rtbd, rtbd_matrix_size, rtbf2 = readOMX(skim_matrix_filename, 'distance', False)
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
        rtbf1.close()
        rtbf2.close()


# ==============================================================================


if __name__ == "__main__":
    main()
