import threading
import time
import argparse
import os
import sys
import pandas as pd

from pynvml import *

from pyJoules.energy_meter import EnergyMeter
from pyJoules.device.rapl_device import RaplDevice
from pyJoules.device import DeviceFactory


class Global:
    interval = 1
    command = None
    csv = False
    verbose = False
    last_reading_timestamp = None
    nvml_joules = None


# @measure_energy(handler=energy_handler, domains=AVAIL_DOMAINS)
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


def get_power_nvml():
    NVIDIA_PREFIX = "nvml_nvidia"

    dict = {}
    for i in range(nvmlDeviceGetCount()):
        handle = nvmlDeviceGetHandleByIndex(i)
        power = nvmlDeviceGetPowerUsage(handle)
        power = power
        dict[f"{NVIDIA_PREFIX}_{i}"] = power

    return dict


def integration_step_nvml():
    power_dict = get_power_nvml()
    now = time.time()
    elapsed = now - Global.last_reading
    for key, power in power_dict.items():
        if key not in Global.nvml_joules:
            Global.nvml_joules[key] = 0
        Global.nvml_joules[key] += power * elapsed
        if Global.verbose:
            print(
                f"Device: {key}. Power: {power} W. Energy: {Global.nvml_joules[key]} J")
    Global.last_reading = now


def integrate_power_nvml():
    Global.last_reading = time.time()
    Global.nvml_joules = {}

    while True:
        integration_step_nvml()
        time.sleep(Global.interval)


def parse_options():

    # Get command to run from args
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <command>")
        sys.exit(1)

    # Options
    args = argparse.ArgumentParser()
    args.add_argument("-c", "--csv", help="CSV output", action="store_true")
    args.add_argument("-v", "--verbose", action="store_true",
                      help="Verbose output")
    args.add_argument("-i", "--interval", type=float,
                      help="Interval to measure power (default 1s)", default=1.0)
    args.add_argument(
        "--nvml", help="Use NVML to measure NVIDIA GPUs power", action="store_true")
    # Rest of the arguments are the command to run
    args.add_argument("command", nargs=argparse.REMAINDER)

    args = args.parse_args()

    if args.interval:
        Global.interval = args.interval

    Global.csv = args.csv
    Global.verbose = args.verbose
    # Get command to run
    Global.command = ' '.join(args.command)


def main():
    parse_options()

    rapl_dev = RaplDevice()
    rapl_avail = rapl_dev.available_domains()

    # Start NVML
    nvmlInit()

    power_thread = threading.Thread(
        target=integrate_power_nvml, daemon=True)
    power_thread.start()

    devices = DeviceFactory.create_devices(rapl_avail)
    meter = EnergyMeter(devices)

    meter.start(tag="command")
    run_command(Global.command)
    meter.stop()

    # Do last integration step before finishing
    integration_step_nvml()
    nvmlShutdown()

    trace = meter.get_trace()

    df = pd.DataFrame()
    for sample in trace:
        sample_dict = {}
        sample_dict["timestamp"] = sample.timestamp
        sample_dict["tag"] = sample.tag
        sample_dict["duration"] = sample.duration
        for domain, energy in sample.energy.items():
            sample_dict[domain] = energy
        sample_df = pd.DataFrame(sample_dict, index=[0])
        df = pd.concat([df, sample_df], ignore_index=True)


    # Append the Global.nvml_joules dict to the dataframe as new columns
    for key, value in Global.nvml_joules.items():
        df[key] = value

    if Global.csv:
        print(df.to_csv(index=False))
    else:
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
