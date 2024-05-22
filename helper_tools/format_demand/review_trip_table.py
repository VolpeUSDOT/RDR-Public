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
    omx_df = f[selectedMatrix]
    if debug_mode:
        print('Sum of matrix elements: {:.9}'.format(np.sum(omx_df)))
        print('Percentiles: ', np.percentile(omx_df, (1, 10, 30, 50, 70, 90, 99)))
        print('Maximum: ', np.amax(omx_df))
    return omx_df, matrix_size, f


# Input arguments
fldr = 'C:/GitHub/RDR/helper_tools/format_demand/matrices'
filename = 'demand_new.omx'
matrix_name = 'matrix'

# Read the input OMX trip table
matrix_filename = os.path.join(fldr, filename)
dem, matrix_size, trip_omx_file = readOMX(matrix_filename, matrix_name, True)

# Example code for analyzing demand matrix
print('Percentiles: ', np.percentile(dem, (1, 25, 50, 75, 99)))

trip_omx_file.close()

