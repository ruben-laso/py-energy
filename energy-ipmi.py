#!/usr/bin/env python3

import pandas as pd

import sys
import os
import argparse
import time
import threading


class Global:
    interval = 1
    command = None
    last_reading = None
    joules = None
    csv = False
    verbose = False
    sudo = False


def run_command(command):
    if Global.verbose:
        print(f"Running command: {command}")
    os.system(command)


def parse_ipmi_output(output):
    df = pd.DataFrame()
    lines = {1: "Power", 2: "Minimum", 3: "Maximum", 4: "Average"}
    i = 1
    for line in output.split("\n"):
        if line == "":
            continue
        if i > len(lines.keys()):
            break
        items = line.split()
        metric = lines.get(i, None)
        val = items[-2]
        units = items[-1]
        df = pd.concat([df, pd.DataFrame(
            {"Metric": [metric], "Value": [val], "Units": [units]})])
        i += 1
    return df


def get_power():
    command = f"ipmitool dcmi power reading"
    if Global.sudo:
        command = f"sudo {command}"
    output = os.popen(command).read()
    if output == "":
        return 0
    df = parse_ipmi_output(output)
    if Global.verbose:
        print(df)
    power = float(df.loc[df["Metric"] == "Power", "Value"].values[0])
    return power


def integration_step():
    power = get_power()
    now = time.time()
    elapsed = now - Global.last_reading
    Global.last_reading = now
    Global.joules += power * elapsed
    if Global.verbose:
        print(f"Power: {power} W. Energy: {Global.joules} J")


def integrate_power():
    Global.last_reading = time.time()
    Global.joules = 0

    while True:
        integration_step()
        time.sleep(Global.interval)


def parse_options():

    # Get command to run from args
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <command>")
        sys.exit(1)

    # Options
    args = argparse.ArgumentParser()
    args.add_argument("-c", "--csv", help="CSV output", action="store_true")
    args.add_argument("-S", "--sudo", help="Run command with sudo",
                      action="store_true")
    args.add_argument("-v", "--verbose", action="store_true",
                      help="Verbose output")
    args.add_argument("-i", "--interval", type=float,
                      help="Interval to measure power (default 1s)", default=1.0)
    # Rest of the arguments are the command to run
    args.add_argument("command", nargs=argparse.REMAINDER)

    args = args.parse_args()

    if args.interval:
        Global.interval = args.interval

    Global.csv = args.csv
    Global.verbose = args.verbose
    Global.sudo = args.sudo

    # Get command to run
    Global.command = ' '.join(args.command)


def main():
    parse_options()

    # Get first reading (in case password is needed)
    get_power()

    tic = time.time()

    power_thread = threading.Thread(target=integrate_power, daemon=True)
    power_thread.start()

    command_thread = threading.Thread(
        target=run_command, args=(Global.command,))
    command_thread.start()

    command_thread.join()

    toc = time.time()

    # Do last integration step before finishing
    integration_step()

    if Global.csv:
        print("Time (s),Energy (J)")
        print(f"{toc - tic},{Global.joules}")
    else:
        print(f"Elapsed {toc - tic} s. Measured energy: {Global.joules} J")


if __name__ == "__main__":
    main()
