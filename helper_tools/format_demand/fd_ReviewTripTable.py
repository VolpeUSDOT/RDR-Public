#!/usr/bin/env python
# coding: utf-8

# Read and summarize OMX trip table and skim file
from os.path import join
import numpy as np
import pandas as pd
import openmatrix as omx


def readOMX(filename, selectedMatrix, debug_mode):
    f = omx.open_file(filename)
    matrix_size = f.shape()
    if (debug_mode):
        print('SelectedMatrix:',selectedMatrix)
        print('Shape:',f.shape())
        print('Number of tables', len(f))
        print('Table names:', f.list_matrices())
        print('attributes:', f.list_all_attributes())
    omx_df = f[selectedMatrix]
    if (debug_mode):
        print('sum of matrix elements', '{:.9}'.format(np.sum(omx_df)))
        print('percentiles', np.percentile(omx_df, (1, 10, 30, 50, 70, 90, 99)))
        print('maximum', np.amax(omx_df))
    return omx_df, matrix_size, f


# Read the input omx trip table
topfldr = 'C:/GitHub/RDR/helper_tools/format_demand'
mtxfldr = join(topfldr, 'matrices')
matrix_filename = join(mtxfldr, 'demand_new.omx')

dem, matrix_size, trip_omx_file = readOMX(matrix_filename, 'matrix', 1)

print('matrix_size:', matrix_size)
print('percentiles', np.percentile(dem, (1, 10, 30, 50, 70, 90, 99)))

dem, matrix_size, trip_omx_file = readOMX(matrix_filename, 'nocar', 1)

print('matrix_size:', matrix_size)
print('percentiles', np.percentile(dem, (1, 10, 30, 50, 70, 90, 99)))


