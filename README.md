# amdgpu_stats

A simple Python module/TUI _(using [Textual](https://textual.textualize.io/))_ that shows AMD GPU statistics

![Screenshot of main screen](https://raw.githubusercontent.com/joshlay/amdgpu_stats/master/screens/main.png "Main screen")

![Screenshot of log screen](https://raw.githubusercontent.com/joshlay/amdgpu_stats/master/screens/logging.png "Logging screen")

The GPU and temperature nodes (`edge`/`junction`/etc.) are discovered automatically.

Statistics are not logged; only toggling Dark/light mode and the stat names / source files.

Tested _only_ on `RX6000` series cards; APUs and more _may_ be supported. Please file an issue if finding incompatibility!

## Requirements
Only `Linux` is supported. Information is _completely_ sourced from interfaces in `sysfs`.

It _may_ be necessary to update the `amdgpu.ppfeaturemask` parameter to enable metrics.

This is assumed present for *control* over the elements being monitored. Untested without. 

See [this Arch Wiki entry](https://wiki.archlinux.org/title/AMDGPU#Boot_parameter) for context.

## Installation / Usage
```
pip install amdgpu-stats
```
Once installed, run `amdgpu-stats` in your terminal of choice

## Module

*Rudimentary* support as a module exists; functions / variables offered can be found in `amdgpu_stats.utils`

Demonstration:
```
In [1]: import amdgpu_stats.utils

In [2]: print(amdgpu_stats.utils.get_core_stats())
{'sclk': 0, 'mclk': 1000000000, 'voltage': 0.01, 'util_pct': 0}

In [3]: print(amdgpu_stats.utils.get_power_stats())
{'limit': 281, 'average': 35, 'capability': 323, 'default': 281}

In [4]: print(amdgpu_stats.utils.get_temp_stats())
{'edge': 33, 'junction': 36, 'mem': 42}

In [5]: print(amdgpu_stats.utils.get_fan_stats())
{'fan_rpm': 0, 'fan_rpm_target': 0}
```
## Documentation

For more information on the module, see:
 - `help('amdgpu_stats.utils')` in your interpreter
 - [ReadTheDocs](https://amdgpu-stats.readthedocs.io/en/latest/)
 - [the module source](https://github.com/joshlay/amdgpu_stats/blob/master/src/amdgpu_stats/utils.py) for more info
