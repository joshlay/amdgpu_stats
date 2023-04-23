# amdgpu_stats

Simple TUI _(using [Textual](https://textual.textualize.io/))_ that shows AMD GPU statistics

- GPU Utilization
- Temperatures _(as applicable)_
    - Edge
    - Junction
    - Memory
- Core clock
- Core voltage
- Memory clock
- Power consumption
- Power limits
    - Default
    - Configured
    - Board capability
 - Fan RPM
    - Current
    - Target

Main screen:
![Screenshot of main screen](https://raw.githubusercontent.com/joshlay/amdgpu_stats/master/screens/main.png "Main screen")

Log screen:
![Screenshot of log screen](https://raw.githubusercontent.com/joshlay/amdgpu_stats/master/screens/logging.png "Logging screen")

Statistics are not logged; only toggling Dark/light mode and the stat names / source files.

Tested _only_ on `RX6000` series cards; more may be supported. Please file an issue if finding incompatibility!

## Requirements
Only `Linux` is supported. Information is _completely_ sourced from interfaces in `sysfs`.

It _may_ be necessary to update the `amdgpu.ppfeaturemask` parameter to enable metrics.

This is assumed present for *control* over the elements being monitored. Untested without. 

See [this Arch Wiki entry](https://wiki.archlinux.org/title/AMDGPU#Boot_parameter) for context.

### Python
The Fedora base repositories provide the requirements with these packages:
 - `python3-humanfriendly`
 - `python3-textual`

See [requirements.txt](requirements.txt) for other distributions
