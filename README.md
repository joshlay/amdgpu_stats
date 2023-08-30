# amdgpu_stats

A Python module/TUI for AMD GPU statistics.
Tested _only_ on `RX6000` series cards and _(less so)_ with Ryzen CPU iGPUs.

Please file an issue if finding incompatibility!

## Screenshots

<details open>
  <summary>Main screen / stats</summary>

  ![Screenshot of the main stats table](https://git.init3.us/BraveTraveler/amdgpu_stats/raw/branch/master/screens/main.svg "Main screen")
</details>
<details>
  <summary>Usage graphs</summary>

  ![Screenshot of the 'graphing' scroll bars](https://git.init3.us/BraveTraveler/amdgpu_stats/raw/branch/master/screens/graphs.svg "Graphs")  
</details>
<details>
  <summary>Logs</summary>

  ![Screenshot of the 'Logs' tab pane](https://git.init3.us/BraveTraveler/amdgpu_stats/raw/branch/master/screens/logs.svg "Logs")
</details>

## Installation
```bash
pip install amdgpu-stats
```
To use the _TUI_, run `amdgpu-stats` in your terminal of choice. For the _module_, see below!

## Module

Introduction:
```python
In [1]: import amdgpu_stats.utils

In [2]: amdgpu_stats.utils.AMDGPU_CARDS
Out[2]: {'card0': '/sys/class/drm/card0/device/hwmon/hwmon9'}

In [3]: amdgpu_stats.utils.get_core_stats('card0')
Out[3]: {'sclk': 640000000, 'mclk': 1000000000, 'voltage': 0.79, 'util_pct': 65}

In [4]: amdgpu_stats.utils.get_clock('core', format_freq=True)
Out[4]: '659 MHz' 
```

For more information on what the module provides, please see:
 - [ReadTheDocs](https://amdgpu-stats.readthedocs.io/en/latest/)
 - `help('amdgpu_stats.utils')` in your interpreter
 - [The module source](https://git.init3.us/BraveTraveler/amdgpu_stats/src/branch/master/src/amdgpu_stats/utils.py)

Feature requests [are encouraged](https://git.init3.us/BraveTraveler/amdgpu_stats/issues) 😀

## Requirements
Only `Linux` is supported. Information is _completely_ sourced from interfaces in `sysfs`.

It _may_ be necessary to update the `amdgpu.ppfeaturemask` parameter to enable metrics.

This is assumed present for *control* over the elements being monitored. Untested without. 

See [this Arch Wiki entry](https://wiki.archlinux.org/title/AMDGPU#Boot_parameter) for context.
