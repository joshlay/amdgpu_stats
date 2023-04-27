"""
utils.py

This module contains utility functions/variables used throughout the 'amdgpu-stats' TUI

Variables:
    - CARD: the identifier for the discovered AMD GPU, ie: `card0` / `card1`
    - hwmon_dir: the `hwmon` interface (dir) that provides stats for this card
    - SRC_FILES: dictionary of the known stats from the items in `hwmon_dir`
    - TEMP_FILES: dictionary of the *discovered* temperature nodes / stat files
    - CLOCK_DOMAINS: tuple of supported clock domains: `core`, `memory`
"""
# disable superfluous linting
# pylint: disable=line-too-long
from os import path
import glob
from typing import Optional, Union
from humanfriendly import format_size


def find_cards() -> dict:
    """Searches contents of `/sys/class/drm/card*/device/hwmon/hwmon*/name`

    Reads 'hwmon' names looking for 'amdgpu' to find cards to monitor.

    If device(s) found, returns a dictionary of cards with their hwmon directories.

    If *none* found, this will be an empty dict.

    Returns:
        dict: `{'cardN': '/hwmon/directory/with/stat/files', 'cardY': '/other/hwmon/directory/for/cardY'}`
    """
    cards = {}
    card_glob_pattern = '/sys/class/drm/card*/device/hwmon/hwmon*/name'
    hwmon_names = glob.glob(card_glob_pattern)
    for hwmon_name_file in hwmon_names:
        with open(hwmon_name_file, "r", encoding="utf-8") as _f:
            if _f.read().strip() == 'amdgpu':
                # found an amdgpu
                _card = hwmon_name_file.split('/')[4]
                _hwmon_dir = path.dirname(hwmon_name_file)
                cards[_card] = _hwmon_dir
    return cards


# discover all available AMD GPUs
AMDGPU_CARDS = find_cards()
# supported clock domains by 'get_clock' func
# is concatenated with 'clock_' to index SRC_FILES for the relevant data file
CLOCK_DOMAINS = ('core', 'memory')
# defined outside/globally for efficiency -- it's called a lot in the TUI


def read_stat(file: str, stat_type: Optional[str] = None) -> str:
    """Read statistic `file`, return the stripped contents

    Args:
        file (str): The statistic file to read/return

        stat_type (str): Optional type, if specified - can convert data.

    Returns:
        str: Statistics from `file`. If `stat_type='power'`, will convert mW to Watts"""
    with open(file, "r", encoding="utf-8") as _fh:
        data = _fh.read().strip()
        if stat_type == 'power':
            data = int(int(data) / 1000000)
    return data


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


def get_power_stats(card: str) -> dict:
    """
    Args:
        card (str): Card identifier from `/dev/dri/`, ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Returns:
        dict: A dictionary of current GPU *power* related statistics.

        Example:
            `{'limit': int, 'average': int, 'capability': int, 'default': int}`
    """
    if card in AMDGPU_CARDS:
        hwmon_dir = AMDGPU_CARDS[card]
    else:
        if len(AMDGPU_CARDS) > 0:
            raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(AMDGPU_CARDS.keys())}")
        raise ValueError(f"Invalid card: '{card}', no AMD GPUs or hwmon directories found")

    return {"limit": read_stat(path.join(hwmon_dir, "power1_cap"), stat_type='power'),
            "average": read_stat(path.join(hwmon_dir, "power1_average"), stat_type='power'),
            "capability": read_stat(path.join(hwmon_dir, "power1_cap_max"), stat_type='power'),
            "default": read_stat(path.join(hwmon_dir, "power1_cap_default"), stat_type='power')}


def get_core_stats(card: str) -> dict:
    """
    Args:
        card (str): Card identifier from `/dev/dri/`, ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Returns:
        dict: A dictionary of current GPU *core/memory* related statistics.

        Clocks are in Hz, the `format_frequency` function may be used to normalize

        Example:
            `{'sclk': int, 'mclk': int, 'voltage': float, 'util_pct': int}`
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    if card in AMDGPU_CARDS:
        return {"sclk": get_clock(card, 'core'),
                "mclk": get_clock(card, 'memory'),
                "voltage": get_voltage(card),
                "util_pct": get_gpu_usage(card)}
    if len(AMDGPU_CARDS) > 0:
        raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(AMDGPU_CARDS.keys())}")
    raise ValueError(f"Invalid card: '{card}', no AMD GPUs or hwmon directories found")


def get_clock(card: str, domain: str, format_freq: bool = False) -> Union[int, str]:
    """
    Args:
        card (str): Card identifier from `/dev/dri/`, ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

        domain (str): The GPU domain of interest regarding clock speed.
            Must be one of CLOCK_DOMAINS

        format_freq (bool, optional): If True, a formatted string will be returned instead of an int.
            Defaults to False.

    Returns:
        Union[int, str]: The clock value for the specified domain.
                         If format_freq is True, a formatted string with Hz/MHz/GHz
                         will be returned instead of an int
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    if card in AMDGPU_CARDS:
        hwmon_dir = AMDGPU_CARDS[card]
    else:
        if len(AMDGPU_CARDS) > 0:
            raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(AMDGPU_CARDS.keys())}")
        raise ValueError(f"Invalid card: '{card}', no AMD GPUs or hwmon directories found")
    if domain not in CLOCK_DOMAINS:
        raise ValueError(f"Invalid clock domain: '{domain}'. Must be one of: {CLOCK_DOMAINS}")
    # set the clock file based on requested domain
    if domain == 'core':
        clock_file = path.join(hwmon_dir, "freq1_input")
    elif domain == 'memory':
        clock_file = path.join(hwmon_dir, "freq2_input")
    # handle output processing
    if format_freq:
        return format_frequency(int(read_stat(clock_file)))
    return int(read_stat(clock_file))


def get_voltage(card: str) -> float:
    """
    Args:
        card (str): Card identifier from `/dev/dri/`, ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Returns:
        float: The current GPU core voltage
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    if card in AMDGPU_CARDS:
        hwmon_dir = AMDGPU_CARDS[card]
    else:
        if len(AMDGPU_CARDS) > 0:
            raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(AMDGPU_CARDS.keys())}")
        raise ValueError(f"Invalid card: '{card}', no AMD GPUs or hwmon directories found")
    return round(int(read_stat(path.join(hwmon_dir, "in0_input"))) / 1000.0, 2)


def get_fan_rpm(card: str) -> int:
    """
    Args:
        card (str): Card identifier from `/dev/dri/`, ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Returns:
        int: The current fan RPM
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    if card in AMDGPU_CARDS:
        hwmon_dir = AMDGPU_CARDS[card]
    else:
        if len(AMDGPU_CARDS) > 0:
            raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(AMDGPU_CARDS.keys())}")
        raise ValueError(f"Invalid card: '{card}', no AMD GPUs or hwmon directories found")
    return int(read_stat(path.join(hwmon_dir, "fan1_input")))


def get_fan_target(card: str) -> int:
    """
    Args:
        card (str): Card identifier from `/dev/dri/`, ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Returns:
        int: The current fan RPM
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    if card in AMDGPU_CARDS:
        hwmon_dir = AMDGPU_CARDS[card]
    else:
        if len(AMDGPU_CARDS) > 0:
            raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(AMDGPU_CARDS.keys())}")
        raise ValueError(f"Invalid card: '{card}', no AMD GPUs or hwmon directories found")
    return int(read_stat(path.join(hwmon_dir, "fan1_target")))


def get_gpu_usage(card: str) -> int:
    """
    Args:
        card (str): Card identifier from `/dev/dri/`, ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Returns:
        int: The current GPU usage/utilization as a percentage
    """
    if card in AMDGPU_CARDS:
        stat_file = path.join("/sys/class/drm/", card, "device/gpu_busy_percent")
    else:
        if len(AMDGPU_CARDS) > 0:
            raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(AMDGPU_CARDS.keys())}")
        raise ValueError(f"Invalid card: '{card}', no AMD GPUs or hwmon directories found")
    return int(read_stat(stat_file))


def get_temp_stats(card: str) -> dict:
    """
    Args:
        card (str): Card identifier from `/dev/dri/`, ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Returns:
        dict: A dictionary of current GPU *temperature* related statistics.

        Example:
            `{'name_temp_node_1': int, 'name_temp_node_2': int, 'name_temp_node_3': int}`

        Dictionary keys (temp nodes) are dynamically contructed through discovery.

        Driver provides temperatures in *millidegrees* C

        Returned values are converted to C, as integers for simple comparison
     """
    if card in AMDGPU_CARDS:
        hwmon_dir = AMDGPU_CARDS[card]
    else:
        if len(AMDGPU_CARDS) > 0:
            raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(AMDGPU_CARDS.keys())}")
        raise ValueError(f"Invalid card: '{card}', no AMD GPUs or hwmon directories found")
    # determine temperature nodes, construct a dict to store them
    # interface will iterate over these, creating labels as needed
    temp_files = {}
    temp_node_labels = glob.glob(path.join(hwmon_dir, "temp*_label"))
    for temp_node_label_file in temp_node_labels:
        # determine the base node id, eg: temp1
        # construct the path to the file that will label it. ie: edge/junction
        temp_node_id = path.basename(temp_node_label_file).split('_')[0]
        temp_node_value_file = path.join(hwmon_dir, f"{temp_node_id}_input")
        with open(temp_node_label_file, 'r', encoding='utf-8') as _node:
            temp_node_name = _node.read().strip()
        # add the node name/type and the corresponding temp file to the dict
        temp_files[temp_node_name] = temp_node_value_file

    temp_update = {}
    for temp_node, temp_file in temp_files.items():
        # iterate through the discovered temperature nodes
        # ... updating the dictionary with new stats
        _temperature = int(int(read_stat(temp_file)) // 1000)
        temp_update[temp_node] = _temperature
    return temp_update
