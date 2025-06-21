#!/usr/bin/env python
# coding: utf-8

# Read and summarize OMX trip table
import os
import numpy as np
import pandas as pd
import openmatrix as omx


def readOMX(filename, selectedMatrix, debug_mode):
    f = omx.open_file(filename)
    matrix_size = f.shape()
    if debug_mode:
        print('Selected matrix: ', selectedMatrix)
        print('Shape: ', f.shape())
        print('Number of tables: ', len(f))
        print('Table names: ', f.list_matrices())
        print('Attributes: ', f.list_all_attributes())
        print('Mappings: ', f.list_mappings())
        if 'taz' in f.list_mappings():
            tazs = f.mapping('taz')
            print('TAZ mappings: ', tazs)
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
    filename = ""
    while not os.path.exists(filename):
        filename = input('----------------------> ').strip('\"')
        print("USER INPUT ----------------->:  {}".format(filename))
        if not os.path.exists(filename):
            print("Path is not valid. Please enter a valid OMX file path.")

    f = omx.open_file(filename)
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

    if matrix_name != "exit":
        # Read the input OMX trip table
        dem, matrix_size, trip_omx_file = readOMX(filename, matrix_name, True)

        trip_omx_file.close()


# ==============================================================================


if __name__ == "__main__":
    main()
