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
# Trip table as an OMX file named baseline_run_demand_summed.omx

# Imports
import os
import pandas as pd
import numpy as np
import openmatrix as omx


def demand_to_omx(input_type, trip_type, matrix_size, trip_csv_file, f_output, output_matrixname, output_od_filename, debug_filename):
    # input_type = 'long' or 'square'
    # trip_type = 'od' or 'pa'
    # matrix_size = number of centroids in the omx matrix
    # trip_csv_file = name of the input csv file containing the trips
    # f_output = file object of output omx file
    # output_matrixname = 'matrix' or 'nocar'
    # output_od_filename = name of od csv file if doing a pa to od conversion
    # debug_filename = name of output square file for debugging
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
    if trip_type == 'pa':
        pivot1 = df_trip.pivot(index='orig_node', columns='dest_node', values='trips')
        pivot2 = df_trip.pivot(index='dest_node', columns='orig_node', values='trips')
        pivot1np = pivot1.to_numpy()
        pivot2np = pivot2.to_numpy()
        pivot1np = np.nan_to_num(pivot1np, nan=0)
        pivot2np = np.nan_to_num(pivot2np, nan=0)
        pivotnp = 0.5 * np.add(pivot1np, pivot2np)
        f_output[output_matrixname] = pivotnp
        np.savetxt(debug_filename, pivotnp, fmt="%.3f", delimiter=",")
        with open(output_od_filename, "w") as textfile:
            print("orig_node,dest_node,trips", file=textfile)
            for i in tazdictrow:
                for j in tazdictrow:
                    print(i, ",", j, ",", pivotnp[tazdictrow[i]][tazdictrow[j]], file=textfile)
    else:
        pivot = df_trip.pivot(index='orig_node', columns='dest_node', values='trips')
        pivotnp = pivot.to_numpy()
        pivotnp = np.nan_to_num(pivotnp, nan=0)
        f_output[output_matrixname] = pivotnp  # Put the filled-in matrix into the OMX file
        pivot.to_csv(debug_filename, index=True)

    return


# ==============================================================================


def main():
    # Input arguments
    print("""Provide the top-level directory path (drag and drop is fine here). This directory must contain:
    - Subfolder called 'matrices' where the OMX output baseline_run_demand_summed.omx will be generated,
    - CSV file named GMNS_node.csv containing the columns 'node_id' and 'node_type', where node_type = 'centroid' for centroid nodes,
    - CSV file called demand.csv in either long or square format,
    - [Optional] CSV file called demand_nocar.csv in either long or square format.
        - If input_type = 'long', the CSV files must have the following columns: orig_node, dest_node, trips.
        - If input_type = 'square', the CSV files must have dimensions of orig_node (first column) and dest_node (first row) with values of trips.
        - The orig_node and dest_node must be centroids.
          """)
    topfldr = ""
    while not os.path.exists(topfldr):
        topfldr = input('----------------------> ').strip('\"')
        print("USER INPUT ----------------->:  {}".format(topfldr))
        if not os.path.exists(topfldr):
            print("Path is not valid. Please enter a valid top-level directory path.")

    mtxfldr = os.path.join(topfldr, 'matrices')
    node_csv_file = os.path.join(topfldr, 'GMNS_node.csv')

    trip_csv_file = os.path.join(topfldr, 'demand.csv')
    nocar_trip_csv_file = os.path.join(topfldr, 'demand_nocar.csv')

    print("Specify the demand file format (either 'long' or 'square'):")
    input_type = ""
    while input_type == "":
        input_type = input('----------------------> ').strip('\"')
        print("USER INPUT ----------------->:  {}".format(input_type))
        if input_type == "exit":
            break
        elif input_type not in ['long', 'square']:
            print("File format type is not valid. Please enter either 'long' or 'square'. Enter 'exit' to exit.")
            input_type = ""

    print("Specify the demand trip type (either 'od' or 'pa'):")
    trip_type = ""
    while trip_type == "":
        trip_type = input('----------------------> ').strip('\"')
        print("USER INPUT ----------------->:  {}".format(trip_type))
        if trip_type == "exit":
            break
        elif trip_type not in ['od', 'pa']:
            print("Demand trip type is not valid. Please enter either 'od' or 'pa'. Enter 'exit' to exit.")
            trip_type = ""

    outfile = os.path.join(mtxfldr, 'baseline_run_demand_summed.omx')

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
    # Set up the omx output
    f_output = omx.open_file(outfile, 'w')
    f_output.create_mapping('taz', taz_list)  # Set up the TAZ mapping
    # Write the dataframe to an OMX file
    # This makes use of tazdictrow and matrix_size that was established earlier
    # The rows are also written to a file that is used for debugging
    # If the trip_type = 'pa' do the pa to od conversion

    demand_to_omx(input_type, trip_type, matrix_size, trip_csv_file, f_output, 'matrix', os.path.join(topfldr, 'demand_od.csv'), os.path.join(topfldr, 'debug_demand.csv'))

    # Code block for optional 'nocar' trip table
    if os.path.exists(nocar_trip_csv_file):
        demand_to_omx(input_type, trip_type, matrix_size, nocar_trip_csv_file, f_output, 'nocar', os.path.join(topfldr, 'demand_od_nocar.csv'), os.path.join(topfldr, 'debug_demand_nocar.csv'))

    f_output.close()  # Close the OMX file


# ==============================================================================


if __name__ == "__main__":
    main()
