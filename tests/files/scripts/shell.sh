#!/bin/bash

# Check if the required positional arguments and keyword argument are provided
if [[ $# -lt 3 ]]; then
  echo "Usage: $0 data1 data2 --input obs_data"
  exit 1
fi

# Assign positional arguments
data1=$1
data2=$2

# Check if the keyword argument --input is provided
if [[ $3 != "--input" ]]; then
  echo "Error: Missing required keyword argument '--input'"
  echo "Usage: $0 data1 data2 --input obs_data"
  exit 1
fi

# Assign the value of --input
obs_data=$4

# Print the arguments to verify
echo "data1: $data1"
echo "data2: $data2"
echo "obs_data: $obs_data"
