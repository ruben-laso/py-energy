#!/usr/bin/env python3

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


def to_joules(df):
    uJ_to_J = 1e-6
    mJ_to_J = 1e-3

    # Remove the "total_energy" column if it exists
    if "total_energy" in df.columns:
        df = df.drop(columns=["total_energy"])

    DICT_COLUMN_TO_SCALE = {
        "package": uJ_to_J,
        "dram": uJ_to_J,
        "core": uJ_to_J,
        "uncore": uJ_to_J,
        "nvidia": mJ_to_J,
    }

    # Scale the columns
    for col in df.columns:
        for col_to_scale in DICT_COLUMN_TO_SCALE:
            if col_to_scale in col:
                df[col] = df[col] * DICT_COLUMN_TO_SCALE[col_to_scale]

    return df


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
    args.add_argument("-j", "--joules", help="Report energy in Joules instead of raw values (which can be uJ, mJ, ...)",
                      action="store_true")
    # Rest of the arguments are the command to run
    args.add_argument("command", nargs=argparse.REMAINDER)

    args = args.parse_args()

    Global.verbose = args.verbose
    Global.csv = args.csv
    Global.joules = args.joules
    if args.file:
        Global.file = args.file

    # Get command to run
    Global.command = ' '.join(args.command)


def main():
    parse_options()

    run_command(Global.command)

    df = energy_handler.get_dataframe()

    if Global.joules:
        df = to_joules(df)

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
