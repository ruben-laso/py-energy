#!/usr/bin/env python3

import time
import argparse
import os
import sys

from pyJoules.energy_meter import measure_energy
from pyJoules.handler.pandas_handler import PandasHandler
energy_handler = PandasHandler()


class Global:
    csv = None
    file = None
    verbose = False
    command = None
    joules = None


@measure_energy(handler=energy_handler)
def run_command(command):
    if Global.verbose:
        print(f"Running command: {command}")
    os.system(command)


def parse_options():

    # Get command to run from args
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <command>")
        sys.exit(1)

    # Options
    args = argparse.ArgumentParser()
    args.add_argument("-c", "--csv", help="CSV output", action="store_true")
    args.add_argument("-f", "--file", help="Output file")
    args.add_argument("-v", "--verbose", help="Verbose mode",
                      action="store_true")
    # Rest of the arguments are the command to run
    args.add_argument("command", nargs=argparse.REMAINDER)

    args = args.parse_args()

    Global.verbose = args.verbose
    Global.csv = args.csv
    if args.file:
        Global.file = args.file

    # Get command to run
    Global.command = ' '.join(args.command)


def main():
    parse_options()

    run_command(Global.command)

    df = energy_handler.get_dataframe()

    # Calculate total energy: add columns after "duration" column
    duration_col = df.columns.get_loc("duration")
    df["total_energy"] = df.iloc[:, duration_col+1:].sum(axis=1)

    # Report output
    if Global.csv:
        if Global.file:
            df.to_csv(Global.file, index=False)
        else:
            print(df.to_csv(index=False))
    else:
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
