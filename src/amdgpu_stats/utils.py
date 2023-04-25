"""
utils.py

This module contains utility functions/variables used throughout 'amdgpu-stats'

Variables:
    - CARD: the identifier for the discovered AMD GPU, ie: `card0` / `card1`
    - hwmon_dir: the `hwmon` interface (dir) that provides stats for this card
    - SRC_FILES: dictionary of the known stats from the items in `hwmon_dir`
    - TEMP_FILES: dictionary of the *discovered* temperature nodes / stat files
"""
from os import path
import glob
from typing import Tuple, Optional
from humanfriendly import format_size


def find_card() -> Optional[Tuple[Optional[str], Optional[str]]]:
    """Searches contents of /sys/class/drm/card*/device/hwmon/hwmon*/name

    ... looking for 'amdgpu' to find a card to monitor

    Returns:
        A tuple containing the 'cardN' name and hwmon directory for stats

    If no AMD GPU found, this will be: (None, None)
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
    """Given statistic file, `file`, return the contents"""
    with open(file, "r", encoding="utf-8") as _fh:
        data = _fh.read()
        return data.strip()


def format_frequency(frequency_hz: int) -> str:
    """Takes a frequency (in Hz) and appends it with the appropriate suffix, ie:
         - Hz
         - MHz
         - GHz"""
    return (
        format_size(frequency_hz, binary=False)
        .replace("B", "Hz")
        .replace("bytes", "Hz")
    )


def get_power_stats() -> dict:
    """
    Returns:
        A dictionary of current GPU *power* related statistics.

        {'limit': int,
         'average': int,
         'capability': int,
         'default': int}
    """
    return {"limit": int(int(read_stat(SRC_FILES['pwr_limit'])) / 1000000),
            "average": int(int(read_stat(SRC_FILES['pwr_average'])) / 1000000),
            "capability": int(int(read_stat(SRC_FILES['pwr_cap'])) / 1000000), 
            "default": int(int(read_stat(SRC_FILES['pwr_default'])) / 1000000)}    


def get_core_stats() -> dict:
    """
    Returns:
        A dictionary of current GPU *core/memory* related statistics.

        {'sclk': int,
         'mclk': int,
         'voltage': float,
         'util_pct': int}

        Clocks are in Hz, `format_frequency` may be used to normalize
    """
    return {"sclk": int(read_stat(SRC_FILES['core_clock'])),
            "mclk": int(read_stat(SRC_FILES['memory_clock'])),
            "voltage": float(
                f"{int(read_stat(SRC_FILES['core_voltage'])) / 1000:.2f}"
            ),
            "util_pct": int(read_stat(SRC_FILES['busy_pct']))}


def get_fan_stats() -> dict:
    """
    Returns:
        A dictionary of current GPU *fan* related statistics.

        {'fan_rpm': int,
         'fan_rpm_target': int}
         """
    return {"fan_rpm": int(read_stat(SRC_FILES['fan_rpm'])),
            "fan_rpm_target": int(read_stat(SRC_FILES['fan_rpm_target']))}


def get_temp_stats() -> dict:
    """
    Returns:
        A dictionary of current GPU *temperature* related statistics.

        Keys/values are dynamically contructed based on discovered nodes

        {'name_temp_node_1': int,
         'name_temp_node_2': int,
         'name_temp_node_3': int}

        Driver provides this in millidegrees C

        Returned values are converted: (floor) divided by 1000 for *proper* C

        As integers for comparison
     """
    temp_update = {}
    for temp_node, temp_file in TEMP_FILES.items():
        # iterate through the discovered temperature nodes
        # ... updating the dictionary with new stats
        _temperature = int(int(read_stat(temp_file)) // 1000)
        temp_update[temp_node] = _temperature
    return temp_update
