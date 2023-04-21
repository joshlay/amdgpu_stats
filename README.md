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

*Note:* Tested _only_ on `RX6000` series cards -- will support more with help, please file an issue.

## Requirements
Only `Linux` is supported. Information heavily relies on the `hwmon` interfaces in `sysfs`.

### Python
The Fedora base repositories provide the requirements with these packages:
 - `python3-humanfriendly`
 - `python3-textual`

See [requirements.txt](requirements.txt) for other distributions

### Kernel
It _may_ be necessary to update the `amdgpu.ppfeaturemask` parameter to enable data collection. 

This is assumed for *control* over the elements being monitored. Untested without. See [this](https://wiki.archlinux.org/title/AMDGPU#Boot_parameter) for context

## Screenshots

Main screen:
![Screenshot of main screen](main.png "Main screen")

Log screen:
![Screenshot of log screen](logging.png "Logging screen")
