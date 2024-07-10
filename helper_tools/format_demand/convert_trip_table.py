#!/usr/bin/env python
# coding: utf-8

# Convert a trip table from a flat file to OMX format
# 
# Inputs:
# 
# Nodes as a CSV flat file in GMNS format with the following columns: node_id, node_type
# - If node_type = 'centroid', then the node is considered a centroid node.
# 
# Trips as one or two CSV flat files
# - If input_type = 'long', the CSV files must have the following columns: orig_node, dest_node, trips.
# - If input_type = 'square', the CSV files must have dimensions of orig_node (first column) and dest_node (first row) with values of trips.
# - The orig_node and dest_node must be centroids.
# - The file demand.csv is required, demand_nocar.csv is optional.
# 
# Outputs:
# 
# Trip table as an OMX file named demand_new.omx

# Imports
import os
import pandas as pd
import numpy as np
import openmatrix as omx

topfldr = 'C:/GitHub/RDR/helper_tools/format_demand'
mtxfldr = os.path.join(topfldr, 'matrices')
node_csv_file = os.path.join(topfldr, 'GMNS_node.csv')

trip_csv_file = os.path.join(topfldr, 'demand.csv')
nocar_trip_csv_file = os.path.join(topfldr, 'demand_nocar.csv')
input_type = 'long'  # Can either be 'long' or 'square'

outfile = os.path.join(mtxfldr, 'demand_new.omx')

# Nodes
# 1. Read the GMNS nodes file into a dataframe
# 2. Set up the dictionary of centroids (to be used when reading in the trip table)
df_node = pd.read_csv(node_csv_file, header=0)
print(df_node.head())

# Set up the dictionary of centroids
# Assumption: node_type = 'centroid' for centroid nodes in GMNS nodes file
# Centroid nodes are the lowest numbered nodes, provided at the beginning of the list of nodes, but node numbers need not be consecutive
tazdictrow = {}
centroid_index = 0
for index in df_node.index:
    if df_node['node_type'][index] == 'centroid':
        tazdictrow[df_node['node_id'][index]] = centroid_index
        centroid_index = centroid_index + 1
taz_list = list(tazdictrow.keys())  # This is the taz mapping that will be used when building the OMX matrix file
matrix_size = len(tazdictrow)  # Should match the number of nodes flagged as centroids
print("Total number of centroids: {}".format(str(matrix_size)))
highest_centroid_node_number = max(tazdictrow, key=tazdictrow.get)
print("Highest centroid node is {}".format(str(highest_centroid_node_number)))

# Read trips and translate to OMX file

# Read a flat file trip table into pandas dataframe
if input_type == 'long':
    df_trip = pd.read_csv(trip_csv_file, header=0)
    print(df_trip.head())
    print("The trip table file {} has size {} by {}".format(trip_csv_file, str(df_trip.shape[0]), str(df_trip.shape[1])))
    print("Total number of trips: {}".format(str(df_trip['trips'].sum())))
elif input_type == 'square':
    df_trip_square = pd.read_csv(trip_csv_file, header=0, index_col=0)
    print(df_trip_square.head())
    print("The trip table file {} has size {} by {}".format(trip_csv_file, str(df_trip_square.shape[0]), str(df_trip_square.shape[1])))
    print("Converting to long file")
    df_trip = df_trip_square.unstack().reset_index(name='trips').rename(columns={'level_1': 'orig_node', 'level_0': 'dest_node'})
    df_trip['orig_node'] = df_trip['orig_node'].astype(int)
    df_trip['dest_node'] = df_trip['dest_node'].astype(int)
    print("Total number of trips: {}".format(str(df_trip['trips'].sum())))

# Sanity check: Number of rows in df_trip can be at most matrix_size * matrix_size
matrix_size_squared = matrix_size * matrix_size
print("Rows in trip_csv_file: {}. Matrix size square: {}.".format(str(df_trip.shape[0]), str(matrix_size_squared)))
if (df_trip.shape[0] > matrix_size_squared):
    print("Error: Number of rows in the CSV file exceeds matrix size squared!")

# Write the dataframe to an OMX file
# This makes use of tazdictrow and matrix_size that was established earlier
# The rows are also written to a file that is used for debugging
f_output = omx.open_file(outfile, 'w')

f_output.create_mapping('taz', taz_list)  # Set up the TAZ mapping
pivot = df_trip.pivot(index='orig_node', columns='dest_node', values='trips')
f_output['matrix'] = pivot.to_numpy()  # Put the filled-in matrix into the OMX file
pivot.to_csv(os.path.join(topfldr, 'debug_demand.csv'), index=True)

# Code block for optional 'nocar' trip table
if os.path.exists(nocar_trip_csv_file):
    if input_type == 'long':
        df_trip = pd.read_csv(nocar_trip_csv_file, header=0)
        print(df_trip.head())
        print("The trip table file {} has size {} by {}".format(nocar_trip_csv_file, str(df_trip.shape[0]), str(df_trip.shape[1])))
        print("Total number of trips: {}".format(str(df_trip['trips'].sum())))
    elif input_type == 'square':
        df_trip_square = pd.read_csv(nocar_trip_csv_file, header=0, index_col=0)
        print(df_trip_square.head())
        print("The trip table file {} has size {} by {}".format(nocar_trip_csv_file, str(df_trip_square.shape[0]), str(df_trip_square.shape[1])))
        print("Converting to long file")
        df_trip = df_trip_square.unstack().reset_index(name='trips').rename(columns={'level_1': 'orig_node', 'level_0': 'dest_node'})
        df_trip['orig_node'] = df_trip['orig_node'].astype(int)
        df_trip['dest_node'] = df_trip['dest_node'].astype(int)
        print("Total number of trips: {}".format(str(df_trip['trips'].sum())))

    pivot = df_trip.pivot(index='orig_node', columns='dest_node', values='trips')
    f_output['nocar'] = pivot.to_numpy()
    pivot.to_csv(os.path.join(topfldr, 'debug_demand_nocar.csv'), index=True)

f_output.close()  # Close the OMX file
