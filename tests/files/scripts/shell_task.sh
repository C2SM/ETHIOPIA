#!/bin/bash

# Dummy script to validate inputs passed via CLI arguments

# Function to extract and print positional arguments, keywords, and flags
process_args() {
  echo "Processing inputs..."
  
  # Arrays to store different types of arguments
  positional=()
  keywords=()
  flags=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --*)  # Keyword arguments or flags
        if [[ "$2" && ! "$2" =~ ^-- ]]; then
          keywords+=("$1=$2")
          shift 2
        else
          flags+=("$1")
          shift
        fi
        ;;
      *)  # Positional arguments
        positional+=("$1")
        shift
        ;;
    esac
  done

  # Print positional arguments
  echo "Positional arguments:"
  for arg in "${positional[@]}"; do
    echo "  $arg"
  done

  # Print keyword arguments
  echo "Keyword arguments:"
  for keyword in "${keywords[@]}"; do
    echo "  $keyword"
  done

  # Print flags
  echo "Flags:"
  for flag in "${flags[@]}"; do
    echo "  $flag"
  done
}

# Process all passed arguments
process_args "$@"

# Test complete
echo "Test complete. All inputs received and categorized." | tee restart
