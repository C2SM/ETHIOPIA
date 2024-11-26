#!/bin/bash

# Function to write text to the output file
write_to_output() {
  local text="$1"
  echo "$text"
  echo "$text" >> output
}

# Check if at least one argument is provided
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 icon_input [--restart [restart_file]]"
  exit 1
fi

# Positional argument
icon_input="$1"

# Optional restart argument
restart_file=""

if [ "$2" == "--restart" ]; then
  if [ -n "$3" ]; then
    restart_file="$3"
  fi
fi

# Create/empty the output file
> output

# Handling restart if the argument is provided
if [ -n "$restart_file" ]; then
  if [ -f "$restart_file" ]; then
    cat "$restart_file" > /dev/null
    write_to_output "Restart operation initiated..."
  else
    echo "Restart file $restart_file does not exist."
    exit 1
  fi
else
  write_to_output "No restart option provided. Continuing without restart."
fi

# Main script execution continues here
write_to_output "Script execution continues..."

# Create/empty the restart file
> restart
