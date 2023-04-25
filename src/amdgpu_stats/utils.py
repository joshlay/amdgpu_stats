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


# utility file -- funcs / constants, intended to provide library function
# function to find the card / hwmon_dir -- assigned to vars, informs consts
def find_card() -> Optional[Tuple[Optional[str], Optional[str]]]:
    """searches contents of /sys/class/drm/card*/device/hwmon/hwmon*/name

    looking for 'amdgpu' to find a card to monitor

    returns the cardN name and hwmon directory for stats"""
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


def read_stat(file: str) -> str:
    """given `file`, return the contents"""
    with open(file, "r", encoding="utf-8") as _fh:
        data = _fh.read().strip()
        return data


def format_frequency(frequency_hz) -> str:
    """takes a frequency and formats it with an appropriate Hz suffix"""
    return (
        format_size(int(frequency_hz), binary=False)
        .replace("B", "Hz")
        .replace("bytes", "Hz")
    )


# globals - card, hwmon directory, and statistic file paths derived from these
CARD, hwmon_dir = find_card()
card_dir = path.join("/sys/class/drm/", CARD)  # eg: /sys/class/drm/card0/
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
TEMP_FILES = {}
# determine temperature nodes, construct an empty dict to store them
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
