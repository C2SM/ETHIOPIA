#!/usr/bin/env python
"""usage: icon.py [-h] [--init [INIT]] [--restart [RESTART]] [--forcing [FORCING]]

A script mocking parts of icon in a form of a shell script

options:
  -h, --help           show this help message and exit
  --init [INIT]        The icon init file.
  --restart [RESTART]  The icon restart file.
  --forcing [FORCING]  The icon forcing file.
"""

import argparse
from pathlib import Path

LOG_FILE = Path("icon.log")

def log(text: str):
    print(text)
    with LOG_FILE.open("a") as f:
        f.write(text)

def main():
    parser = argparse.ArgumentParser(description='A script mocking parts of icon in a form of a shell script.')
    parser.add_argument('--init', nargs='?', type=str, help='The icon init file.')
    parser.add_argument('--restart', nargs='?', type=str, help='The icon restart file.')
    parser.add_argument('--forcing', nargs='?', type=str, help='The icon forcing file.')
    #parser.add_argument('--restart', nargs='?', const='default', type=str, help='Initiate a restart operation with an optional string argument.')


    args = parser.parse_args()
    

    output = Path('icon_output')
    output.write_text("")

    if args.restart and args.init:
        raise ValueError("Cannot use '--init' and '--restart' option at the same time.")
    elif args.restart:
        if not Path(args.restart).exists():
            raise FileNotFoundError(f"The icon restart file {args.restart!r} was not found.")
        restart = Path(args.restart)

        log(f"Restarting from file {args.restart!r}.")
    elif args.init:
        if not Path(args.init).exists():
            raise FileNotFoundError(f"The icon init file {args.init!r} was not found.")

        log(f"Starting from init file {args.init!r}.")
    else: 
        raise ValueError("Please provide a restart or init file with the corresponding option.")

    # Main script execution continues here
    log("Script finished running calculations")

    restart = Path('restart')
    restart.write_text("")

if __name__ == '__main__':
    main()


