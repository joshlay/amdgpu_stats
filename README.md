# amdgpu_stats

A simple Python module/TUI _(using [Textual](https://textual.textualize.io/))_ that shows AMD GPU statistics

![Screenshot of main screen](https://raw.githubusercontent.com/joshlay/amdgpu_stats/master/screens/main.png "Main screen")

The GPU and temperature nodes (`edge`/`junction`/etc.) are discovered automatically.

Please see [the module section](#module) or [the docs](https://amdgpu-stats.readthedocs.io/en/latest/) for information on usage as an `import` in other tooling

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

In [2]: amdgpu_stats.utils.AMDGPU_CARDS
Out[2]: {'card0': '/sys/class/drm/card0/device/hwmon/hwmon9'}

In [3]: amdgpu_stats.utils.get_core_stats('card0')
Out[3]: {'sclk': 640000000, 'mclk': 1000000000, 'voltage': 0.79, 'util_pct': 65}

In [4]: amdgpu_stats.utils.get_clock('card0', 'core', format_freq=True)
Out[4]: '659 MHz' 
```
Feature requests [are encouraged](https://github.com/joshlay/amdgpu_stats/issues) :)

## Documentation

For more information on the module, see:
 - `help('amdgpu_stats.utils')` in your interpreter
 - [ReadTheDocs](https://amdgpu-stats.readthedocs.io/en/latest/)
 - [the module source](https://github.com/joshlay/amdgpu_stats/blob/master/src/amdgpu_stats/utils.py) for more info
