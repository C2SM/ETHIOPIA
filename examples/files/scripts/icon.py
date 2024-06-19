#!/usr/bin/env python

import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='A simple script with an optional restart argument.')
    parser.add_argument('icon_input', type=str, help='The icon input.')
    parser.add_argument('--restart', nargs='?', type=str, help='The icon restart file.')
    #parser.add_argument('--restart', nargs='?', const='default', type=str, help='Initiate a restart operation with an optional string argument.')


    args = parser.parse_args()

    output = Path('output')
    output.write_text("")

    if args.restart:
        restart = Path(args.restart)
        restart.read_text()
        text = "Restart operation initiated..."
        print(text)
        with output.open("a") as f:
            f.write(text)
    else:
        text = "No restart option provided. Continuing without restart."
        print(text)
        with output.open("a") as f:
            f.write(text)

    # Main script execution continues here
    text = "Script execution continues..."
    print(text)
    with output.open("a") as f:
        f.write(text)

    restart = Path('restart')
    restart.write_text("")

if __name__ == '__main__':
    main()
