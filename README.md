# amdgpu_stats

Simple TUI _(using [Textual](https://textual.textualize.io/))_ that shows AMD GPU statistics:
 - GPU Utilization
 - Temperature
 - Core clock
 - Core voltage
 - Memory clock
 - Power consumption
 - Power limits
   - Default
   - Configured
   - Board capability

## Requirements

It _may_ be necessary to update the `amdgpu.ppfeaturemask` parameter to enable data collection. 

This is assumed for *control* over the elements being monitored. Untested without. See [this Arch Wiki doc](https://wiki.archlinux.org/title/AMDGPU#Boot_parameter) for context

The following unusual modules are required:
 - [textual](https://textual.textualize.io/reference/)
 - [humanfriendly](https://pypi.org/project/humanfriendly/)

This list *may not* be maintained; consider imports / your environment

## Screenshots

Main screen:
![Screenshot of main screen](main.png "Main screen")

Log screen:
![Screenshot of log screen](logging.png "Logging screen")
