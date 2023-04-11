#!/usr/bin/env python
# coding: utf-8


# Convert a trip table from flat file to OMX
# 
# Inputs:
# 
# Nodes as a .csv flat file in GMNS format
# - Critical fields include node_id and node_type. If node_type = 'centroid', then the node is a centroid node
# 
# Trips as one or two .csv flat files, with the following columns: orig_node, dest_node, trips
# - The orig_node and dest_node must be centroids
# - demand.csv is required,  demand_nocar.csv is optional
# 
# Output:
# 
# Trip table as an omx file, named demand_new.omx

# Imports
from os.path import join
import pandas as pd
import numpy as np
import openmatrix as omx

topfldr = 'C:/GitHub/RDR/helper_tools/format_demand'
mtxfldr = join(topfldr,'matrices')

# ## Nodes
# 1. Read the GMNS nodes into a dataframe
# 2. Set up the dictionary of centroids (will be used later when reading the trip table)

node_csv_file = join(topfldr, "GMNS_node.csv")
df_node = pd.read_csv(node_csv_file)
df_node  #DEBUG

# Set up the dictionary of centroids
# Assumption: the node_type = 'centroid' for centroid nodes
# The centroid nodes are the lowest numbered nodes, at the beginning of the list of nodes,
# but node numbers need not be consecutive
tazdictrow = {}
centroid_index = 0;
for index in df_node.index:
    if df_node['node_type'][index]=='centroid':
        #DEBUG print(index, df_node['node_id'][index], df_node['node_type'][index])
        tazdictrow[df_node['node_id'][index]]=centroid_index  ## Using centroid_index
        centroid_index = centroid_index + 1
taz_list = list(tazdictrow.keys())  # This is the taz mapping that will be used when building the omx matrix file
matrix_size = len(tazdictrow)  # Matches the number of nodes flagged as centroids
print(matrix_size)  #DEBUG
highest_centroid_node_number = max(tazdictrow, key=tazdictrow.get)  #DEBUG for future use
print(highest_centroid_node_number)  #DEBUG

# Read the trips and translate to omx file

# Read a flat file trip table into pandas dataframe
trip_csvfile = join(topfldr, 'demand.csv')
df_trip = pd.read_csv(trip_csvfile)  # data already has headers
print(df_trip.head())  #DEBUG
df_size = df_trip.shape[0]
print(trip_csvfile, 'Size =', df_size)  #DEBUG
# stuff for debugging
print(df_trip['trips'].sum())  # for debugging: total number of trips

# Sanity check: df_size can be at most matrix_size * matrix_size
matrix_size_squared = matrix_size * matrix_size
print('Rows in trip_csvfile:', df_size, '   Matrix size squared:', matrix_size_squared)
if (df_size > matrix_size_squared):
    print("Error. Rows in the csv file exceeds matrix size squared!")

# Write the dataframe to an omx file
# This makes use of tazdictrow and matrix_size, that was established earlier
# The rows are also written to a file that is used only for debugging

outfile = join(mtxfldr, 'demand_new.omx')
outdebugfile = open(join(topfldr, 'debug_demand.txt'), "w")  #DEBUG
output_demand = np.zeros((matrix_size, matrix_size))  # Create an empty square matrix
f_output = omx.open_file(outfile, 'w')

f_output.create_mapping('taz', taz_list)  # Set up the TAZ mapping
# write the data
for k in range(df_size):  # at most matrix_size * matrix_size
    i = tazdictrow[df_trip.iloc[k]['orig_node']]
    j = tazdictrow[df_trip.iloc[k]['dest_node']]
  
    output_demand[i][j] = df_trip.iloc[k]['trips']
    print('Row: ', df_trip.iloc[k]['orig_node'], i, "  Col: ", df_trip.iloc[k]['dest_node'], j, " Output", output_demand[i][j], file=outdebugfile)
   
f_output['matrix'] = output_demand  # Put the filled-in matrix into the OMX file

#  New code block for demand_nocar  (used in transit)
try:
    trip_csvfile = join(topfldr, 'demand_nocar.csv')
    df_trip = pd.read_csv(trip_csvfile)  # data already has headers
    print(df_trip.head())  #DEBUG
    df_size = df_trip.shape[0]
    print(trip_csvfile, 'Size =', df_size)  #DEBUG
    # stuff for debugging
    print(df_trip['trips'].sum()) 
    output_demand_nocar = np.zeros((matrix_size, matrix_size))
    for k in range(df_size):  # at most matrix_size * matrix_size
        i = tazdictrow[df_trip.iloc[k]['orig_node']]
        j = tazdictrow[df_trip.iloc[k]['dest_node']]
        output_demand_nocar[i][j] = df_trip.iloc[k]['trips']
    f_output['nocar'] = output_demand_nocar
except:
	print("Exception on reading and processing demand_nocar")
f_output.close()  # close the OMX and debugging files
outdebugfile.close()

