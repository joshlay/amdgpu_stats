# amdgpu_stats

Simple TUI _(using [Textual](https://textual.textualize.io/))_ that shows AMD GPU statistics

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

Of most interest:
 - The function `find_card` which returns a tuple; the discovered card and hwmon directory
 - The variables `SRC_FILES` and `TEMP_FILES`, dictionaries of hwmon-driven statistics

Example usage:
```
In [1]: from amdgpu_stats.utils import find_card, SRC_FILES, TEMP_FILES

In [2]: print(find_card())
('card0', '/sys/class/drm/card0/device/hwmon/hwmon9')

In [3]: print(SRC_FILES)
{'pwr_limit': '/sys/class/drm/card0/device/hwmon/hwmon9/power1_cap', 'pwr_average': '/sys/class/drm/card0/device/hwmon/hwmon9/power1_average',
[...]

In [4]: print(TEMP_FILES)
{'edge': '/sys/class/drm/card0/device/hwmon/hwmon9/temp1_input', 'junction': '/sys/class/drm/card0/device/hwmon/hwmon9/temp2_input', 'mem': '/sys/class/drm/card0/device/hwmon/hwmon9/temp3_input'}
```
_Latest_ [Source file](https://github.com/joshlay/amdgpu_stats/blob/master/src/amdgpu_stats/utils.py)
