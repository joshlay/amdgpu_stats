"""
utils.py

This module contains utility functions/variables used throughout the 'amdgpu-stats' TUI

Variables:
    - AMDGPU_CARDS (dict): discovered AMD GPUs and their `hwmon` stats directories
        - Example: `{'card0': '/sys/class/drm/card0/device/hwmon/hwmon9'}`
        - If no *AMD* cards are found, this will be empty.
    - CLOCK_DOMAINS (tuple): supported clock domains, ie: `('core', 'memory')`
"""
# disable superfluous linting
# pylint: disable=line-too-long
from os import path
import glob
from typing import Optional, Union
from humanfriendly import format_size


def find_cards() -> dict:
    """
    Searches contents of `/sys/class/drm/card*/device/hwmon/hwmon*/name`

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
    return dict(sorted(cards.items()))


# discover all available AMD GPUs
AMDGPU_CARDS = find_cards()
# supported clock domains by 'get_clock' func
# is concatenated with 'clock_' to index SRC_FILES for the relevant data file
CLOCK_DOMAINS = ('core', 'memory')
# defined outside/globally for efficiency -- it's called a lot in the TUI


def validate_card(card: Optional[str] = None) -> str:
    """
    Checks the provided `card` identifier -- if present in `AMDGPU_CARDS`

    If `card` is not provided, will yield the first AMD GPU *(if any installed)*

    Args:
        card (str, optional): ie: `card0`.

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.
            Determined with `AMDGPU_CARDS`

    Returns:
        str: Validated card identifier. 
            If `card` is provided and valid: original identifier `card` is returned
            If `card` is omitted: the first AMD GPU identifier is returned
    """
    if card in AMDGPU_CARDS:
        # card was provided and checks out, send it back
        return card
    if card is None:
        # if no card provided and we know some, send the first one we know back
        if len(AMDGPU_CARDS) > 0:
            return list(AMDGPU_CARDS.keys())[0]
        # if no AMD cards found, toss an errror
        raise ValueError("No AMD GPUs or hwmon directories found")
    # if 'card' was specified (not None) but invalid (not in 'AMDGPU_CARDS'), raise a helpful error
    raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(AMDGPU_CARDS.keys())}")


def read_stat(file: str, stat_type: Optional[str] = None) -> str:
    """
    Read statistic `file`, return the stripped contents

    Args:
        file (str): The statistic file to read/return

        stat_type (str): Optional type, if specified - can convert data.

    Returns:
        str: Statistics from `file`. If `stat_type='power'`, will convert mW to Watts
    """
    if path.exists(file):
        with open(file, "r", encoding="utf-8") as _fh:
            data = _fh.read().strip()
            if stat_type == 'power':
                data = int(int(data) / 1000000)
            return data
    else:
        return None



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


def get_power_stats(card: Optional[str] = None) -> dict:
    """
    Args:
        card (str, optional): ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.
            Determined with `AMDGPU_CARDS`

    Returns:
        dict: A dictionary of current GPU *power* related statistics.

        Example:
            `{'limit': int, 'average': int, 'capability': int, 'default': int}`
    """
    card = validate_card(card)
    hwmon_dir = AMDGPU_CARDS[card]
    _pwr = {"limit": read_stat(path.join(hwmon_dir, "power1_cap"), stat_type='power'),
            "limit_pct": 0,
            "average": read_stat(path.join(hwmon_dir, "power1_average"), stat_type='power'),
            "capability": read_stat(path.join(hwmon_dir, "power1_cap_max"), stat_type='power'),
            "default": read_stat(path.join(hwmon_dir, "power1_cap_default"), stat_type='power')}

    if _pwr['limit'] is not None:
        _pwr['limit_pct'] = round((_pwr['average'] / _pwr['limit']) * 100, 1)

    return _pwr


def get_core_stats(card: Optional[str] = None) -> dict:
    """
    Args:
        card (str, optional): ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.
            Determined with `AMDGPU_CARDS`

    Returns:
        dict: A dictionary of current GPU *core/memory* related statistics.

        Clocks are in Hz, the `format_frequency` function may be used to normalize

        Example:
            `{'sclk': int, 'mclk': int, 'voltage': float, 'util_pct': int}`
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    card = validate_card(card)
    return {"sclk": get_clock('core', card=card),
            "mclk": get_clock('memory', card=card),
            "voltage": get_voltage(card),
            "util_pct": get_gpu_usage(card)}


def get_clock(domain: str, card: Optional[str] = None, format_freq: Optional[bool] = False) -> Union[int, str]:
    """
    Args:
        domain (str): The GPU part of interest RE: clock speed.
            Must be either 'core' or 'memory'

        card (str, optional): ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

        format_freq (bool, optional): If True, a formatted string will be returned instead of an int.
            Defaults to False.

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.
            Determined with `AMDGPU_CARDS`

    Returns:
        Union[int, str]: The clock value for the specified domain.
                         If format_freq is True, a formatted string with Hz/MHz/GHz
                         will be returned instead of an int

        None:            The clock domain is invalid for *card*
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    card = validate_card(card)
    hwmon_dir = AMDGPU_CARDS[card]
    if domain not in CLOCK_DOMAINS:
        raise ValueError(f"Invalid clock domain: '{domain}'. Must be one of: {CLOCK_DOMAINS}")
    # set the clock file based on requested domain
    if domain == 'core':
        clock_file = path.join(hwmon_dir, "freq1_input")
    elif domain == 'memory':
        clock_file = path.join(hwmon_dir, "freq2_input")
    # handle output processing
    # check if clock file exists, if not - return 'none'
    if path.exists(clock_file):
        if format_freq:
            return format_frequency(int(read_stat(clock_file)))
        return int(read_stat(clock_file))
    return None


def get_voltage(card: Optional[str] = None) -> float:
    """
    Args:
        card (str, optional): ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.
            Determined with `AMDGPU_CARDS`

    Returns:
        float: The current GPU core voltage
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    card = validate_card(card)
    hwmon_dir = AMDGPU_CARDS[card]
    return round(int(read_stat(path.join(hwmon_dir, "in0_input"))) / 1000.0, 2)


def get_fan_rpm(card: Optional[str] = None) -> int:
    """
    Args:
        card (str, optional): ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.
            Determined with `AMDGPU_CARDS`


    Returns:
        int: The *current* fan RPM
        None: If *card* does not have a fan
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    card = validate_card(card)
    hwmon_dir = AMDGPU_CARDS[card]
    _val = read_stat(path.join(hwmon_dir, "fan1_input"))
    if _val is not None:
        _val = int(_val)
    return _val


def get_fan_target(card: Optional[str] = None) -> int:
    """
    Args:
        card (str, optional): ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.
            Determined with `AMDGPU_CARDS`

    Returns:
        int: The *target* fan RPM
    """
    # verify card -- is it AMD, do we know the hwmon directory?
    card = validate_card(card)
    hwmon_dir = AMDGPU_CARDS[card]
    return int(read_stat(path.join(hwmon_dir, "fan1_target")))


def get_gpu_usage(card: Optional[str] = None) -> int:
    """
    Args:
        card (str, optional): ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.
            Determined with `AMDGPU_CARDS`

    Returns:
        int: The current GPU usage/utilization as a percentage
    """
    card = validate_card(card)
    stat_file = path.join("/sys/class/drm/", card, "device/gpu_busy_percent")
    return int(read_stat(stat_file))


def get_available_temps(card: Optional[str] = None) -> dict:
    """
    Args:
        card (str, optional): ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.

    Returns:
        dict: Discovered temperature `nodes` and paths to their value files

        If none are found, will be empty.

        Example:
            `{'edge': '/.../temp1_input', 'junction': '/.../temp2_input', 'mem': '/.../temp3_input'}`
    """
    card = validate_card(card)
    hwmon_dir = AMDGPU_CARDS[card]
    # determine temperature nodes/types, construct a dict to store them
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
    return temp_files


def get_temp_stat(name: str, card: Optional[str] = None) -> dict:
    """
    Args:
        card (str, optional): ie: `card0`. See `AMDGPU_CARDS` or `find_cards()`
        name (str): temperature *name*, ie: `edge`, `junction`, or `mem`

    Raises:
        ValueError: If *no* AMD cards are found, or `card` is not one of them.
            *Or* Invalid temperature name is provided.

    Returns:
        int: Requested GPU temperature (type, by `name`).
            Either the first AMD card, or one specified with `card=`.

        Driver provides temperatures in *millidegrees* C

        Returned values are converted to 'C' as integers for simple comparison
    """
    card = validate_card(card)
    # determine temperature nodes/types, construct a dict to store them
    temp_files = get_available_temps(card=card)

    # now that we know the temperature nodes/types for 'card', check request
    if name not in temp_files:
        return None

    # if the requested temperature node was found, read it / convert to C
    return int(int(read_stat(temp_files[name])) // 1000)
