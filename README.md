# amdgpu_stats

A Python module/TUI for AMD GPU statistics. Please [file an issue](https://github.com/joshlay/amdgpu_stats/issues)
with feature requests or bug reports!

## Screenshots

<details open>
  <summary>Main screen / stats</summary>

  ![Screenshot of the main stats table](https://raw.githubusercontent.com/joshlay/amdgpu_stats/master/screens/main.svg "Main screen")
</details>
<details>
  <summary>Usage graphs</summary>

  ![Screenshot of the 'graphing' scroll bars](https://raw.githubusercontent.com/joshlay/amdgpu_stats/master/screens/graphs.svg "Graphs")  
</details>
<details>
  <summary>Logs</summary>

  ![Screenshot of the 'Logs' tab pane](https://raw.githubusercontent.com/joshlay/amdgpu_stats/master/screens/logs.svg "Logs")
</details>

## Installation

```bash
pip install amdgpu-stats
```

To use the _TUI_, run `amdgpu-stats` in your terminal of choice. For the _module_,
see below!

## Module

Introduction:

```python
In [1]: import amdgpu_stats.utils

In [2]: amdgpu_stats.utils.CARDS
Out[2]: {'card0': '/sys/class/drm/card0/device/hwmon/hwmon9'}

In [3]: amdgpu_stats.utils.get_core_stats('card0')
Out[3]: {'sclk': 640000000, 'mclk': 1000000000, 'voltage': 0.79, 'util_pct': 65}

In [4]: amdgpu_stats.utils.get_clock('core', format_freq=True)
Out[4]: '659 MHz' 
```

Attempts are made to provide guidance as `ValueErrors`. For example:

```python
In [2]: amdgpu_stats.utils.CARDS
Out[2]: {'card1': '/sys/class/drm/card1/device/hwmon/hwmon3'}

In [3]: amdgpu_stats.utils.get_core_stats('card0')
[...]
File ~/.local/lib/python3.12/site-packages/amdgpu_stats/utils.py:82, in validate_card(card)
     80     raise ValueError("No AMD GPUs or hwmon directories found")
     81 # if 'card' was specified (not None) but invalid (not in 'CARDS'), raise a helpful error
---> 82 raise ValueError(f"Invalid card: '{card}'. Must be one of: {list(CARDS.keys())}")

ValueError: Invalid card: 'card0'. Must be one of: ['card1']
```

For more information on what the module provides, please see:

- [ReadTheDocs](https://amdgpu-stats.readthedocs.io/en/latest/)
- `help('amdgpu_stats.utils')` in your interpreter
- [The module source](https://github.com/joshlay/amdgpu_stats/blob/master/src/amdgpu_stats/utils.py)

## Requirements

Only `Linux` is supported. Information is _completely_ sourced from `sysfs`.
