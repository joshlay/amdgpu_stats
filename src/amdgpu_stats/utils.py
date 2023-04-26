"""
utils.py

This module contains utility functions/variables used throughout the 'amdgpu-stats' TUI

Variables:
    - CARD: the identifier for the discovered AMD GPU, ie: `card0` / `card1`
    - hwmon_dir: the `hwmon` interface (dir) that provides stats for this card
    - SRC_FILES: dictionary of the known stats from the items in `hwmon_dir`
    - TEMP_FILES: dictionary of the *discovered* temperature nodes / stat files
    - POWER_DOMAINS: tuple of supported power domains: `average`, `limit`, `cap`, and `default`
    - CLOCK_DOMAINS: tuple of supported clock domains: `core`, `memory`
"""
# disable superfluous linting
# pylint: disable=line-too-long
from os import path
import glob
from typing import Tuple, Optional, Union
from humanfriendly import format_size


def find_card() -> Optional[Tuple[Optional[str], Optional[str]]]:
    """Searches contents of /sys/class/drm/card*/device/hwmon/hwmon*/name

    ... looking for 'amdgpu' to find a card to monitor

    If no AMD GPU found, this will be: (None, None)

    Returns:
        tuple: ('cardN', '/hwmon/directory/with/stat/files')
    """
    _card = None
    _hwmon_dir = None
    hwmon_names_glob = '/sys/class/drm/card*/device/hwmon/hwmon*/name'
    hwmon_names = glob.glob(hwmon_names_glob)
    for hwmon_name_file in hwmon_names:
        with open(hwmon_name_file, "r", encoding="utf-8") as _f:
            if _f.read().strip() == 'amdgpu':
                # found an amdgpu
                # note: if multiple are found, last will be used/watched
                # will be configurable in the future, may prompt
                _card = hwmon_name_file.split('/')[4]
                _hwmon_dir = path.dirname(hwmon_name_file)
    return _card, _hwmon_dir


# base vars: card identifier, hwmon directory for stats, then the stat dicts
CARD, hwmon_dir = find_card()
if CARD is not None:
    card_dir = path.join("/sys/class/drm/", CARD)  # eg: /sys/class/drm/card0/

    # dictionary of known source files
    # ref: https://docs.kernel.org/gpu/amdgpu/thermal.html
    SRC_FILES = {'pwr_limit': path.join(hwmon_dir, "power1_cap"),
                 'pwr_average': path.join(hwmon_dir, "power1_average"),
                 'pwr_cap': path.join(hwmon_dir, "power1_cap_max"),
                 'pwr_default': path.join(hwmon_dir, "power1_cap_default"),
                 'core_clock': path.join(hwmon_dir, "freq1_input"),
                 'core_voltage': path.join(hwmon_dir, "in0_input"),
                 'memory_clock': path.join(hwmon_dir, "freq2_input"),
                 'busy_pct': path.join(card_dir, "device/gpu_busy_percent"),
                 'temp_c': path.join(hwmon_dir, "temp1_input"),
                 'fan_rpm': path.join(hwmon_dir, "fan1_input"),
                 'fan_rpm_target': path.join(hwmon_dir, "fan1_target"),
                 }

    # determine temperature nodes, construct a dict to store them
    # interface will iterate over these, creating labels as needed
    TEMP_FILES = {}
    temp_node_labels = glob.glob(path.join(hwmon_dir, "temp*_label"))
    for temp_node_label_file in temp_node_labels:
        # determine the base node id, eg: temp1
        # construct the path to the file that will label it. ie: edge/junction
        temp_node_id = path.basename(temp_node_label_file).split('_')[0]
        temp_node_value_file = path.join(hwmon_dir, f"{temp_node_id}_input")
        with open(temp_node_label_file, 'r', encoding='utf-8') as _node:
            temp_node_name = _node.read().strip()
        # add the node name/type and the corresponding temp file to the dict
        TEMP_FILES[temp_node_name] = temp_node_value_file


def read_stat(file: str) -> str:
    """Read statistic `file`, return the stripped contents

    Returns:
        str: Statistics from `file`"""
    with open(file, "r", encoding="utf-8") as _fh:
        data = _fh.read()
        return data.strip()


def format_frequency(frequency_hz: int) -> str:
    """
    Takes a frequency (in Hz) and normalizes it: `Hz`, `MHz`, or `GHz`

    Returns:
        str: frequency string with the appropriate suffix applied
    """
    return (
        format_size(frequency_hz, binary=False)
        .replace("B", "Hz")
        .replace("bytes", "Hz")
    )


def get_power_stats() -> dict:
    """
    Returns:
        dict: A dictionary of current GPU *power* related statistics.

        Example:
            `{'limit': int, 'average': int, 'capability': int, 'default': int}`
    """
    return {"limit": get_gpu_power('limit'),
            "average": get_gpu_power('average'),
            "capability": get_gpu_power('cap'),
            "default": get_gpu_power('default')}


# constant; supported power domains by 'get_gpu_power' func
# is concatenated with 'pwr_' to index SRC_FILES for the relevant data file
POWER_DOMAINS = ('limit', 'average', 'cap', 'default')
# defined outside/globally for efficiency -- it's called a lot in the TUI


def get_gpu_power(domain: str) -> int:
    """
    Args:
        domain (str): The GPU domain of interest regarding power

                      Must be one of POWER_DOMAINS:
                       - limit: the effective limit placed on the card
                       - default: the default limit
                       - average: the average consumption
                       - cap: the board capability

    Returns:
        int: The requested GPU power statistic by domain, in Watts
    """
    if domain not in POWER_DOMAINS:
        raise ValueError(f"Invalid power domain: '{domain}'. Must be one of: {POWER_DOMAINS}")
    return int(int(read_stat(SRC_FILES['pwr_' + domain])) / 1000000)


def get_core_stats() -> dict:
    """
    Returns:
        dict: A dictionary of current GPU *core/memory* related statistics.

        Clocks are in Hz, the `format_frequency` function may be used to normalize

        Example:
            `{'sclk': int, 'mclk': int, 'voltage': float, 'util_pct': int}`
    """
    return {"sclk": get_clock('core'),
            "mclk": get_clock('memory'),
            "voltage": get_voltage(),
            "util_pct": get_gpu_usage()}


# constant; supported clock domains by 'get_clock' func
# is concatenated with 'clock_' to index SRC_FILES for the relevant data file
CLOCK_DOMAINS = ('core', 'memory')
# defined outside/globally for efficiency -- it's called a lot in the TUI


def get_clock(domain: str, format_freq: bool = False) -> Union[int, str]:
    """
    Args:
        domain (str): The GPU domain of interest regarding clock speed.
            Must be one of CLOCK_DOMAINS

        format_freq (bool, optional): If True, a formatted string will be returned instead of an int.
            Defaults to False.

    Returns:
        Union[int, str]: The clock value for the specified domain.
                         If format_freq is True, a formatted string with Hz/MHz/GHz
                         will be returned instead of an int
    """
    if domain not in CLOCK_DOMAINS:
        raise ValueError(f"Invalid clock domain: '{domain}'. Must be one of: {CLOCK_DOMAINS}")
    if format_freq:
        return format_frequency(read_stat(SRC_FILES[domain + '_clock']))
    return int(read_stat(SRC_FILES[domain + '_clock']))


def get_voltage() -> float:
    """
    Returns:
        float: The current GPU core voltage
    """
    return round(int(read_stat(SRC_FILES['core_voltage'])) / 1000.0, 2)


def get_fan_stats() -> dict:
    """
    Returns:
        dict: A dictionary of current GPU *fan* related statistics.

        Example:
            `{'fan_rpm': int, 'fan_rpm_target': int}`
    """
    return {"fan_rpm": get_fan_rpm(),
            "fan_rpm_target": get_fan_target()}


def get_fan_rpm() -> int:
    """
    Returns:
        int: The current fan RPM
    """
    return int(read_stat(SRC_FILES['fan_rpm']))


def get_fan_target() -> int:
    """
    Returns:
        int: The current fan RPM
    """
    return int(read_stat(SRC_FILES['fan_rpm_target']))


def get_gpu_usage() -> int:
    """
    Returns:
        int: The current GPU usage/utilization as a percentage
    """
    return int(read_stat(SRC_FILES['busy_pct']))


def get_temp_stats() -> dict:
    """
    Returns:
        dict: A dictionary of current GPU *temperature* related statistics.

        Example:
            `{'name_temp_node_1': int, 'name_temp_node_2': int, 'name_temp_node_3': int}`

        Dictionary keys (temp nodes) are dynamically contructed through discovery.

        Driver provides temperatures in *millidegrees* C

        Returned values are converted to C, as integers for simple comparison
     """
    temp_update = {}
    for temp_node, temp_file in TEMP_FILES.items():
        # iterate through the discovered temperature nodes
        # ... updating the dictionary with new stats
        _temperature = int(int(read_stat(temp_file)) // 1000)
        temp_update[temp_node] = _temperature
    return temp_update
