#!/usr/bin/python3
"""Pretty Textual-based stats for AMD GPUs

TODO: restore argparse / --card, in case detection fails.
      will require separating the hwmon finding tasks from 'find_card'

rich markup reference:
    https://rich.readthedocs.io/en/stable/markup.html
"""
from os import path
import glob
import sys
from typing import Tuple, Optional

from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, TextLog, Label
from humanfriendly import format_size


# function to find the card / hwmon_dir -- assigned to vars, informs consts
def find_card() -> Optional[Tuple[Optional[str], Optional[str]]]:
    """searches contents of /sys/class/drm/card*/device/hwmon/hwmon*/name

    looking for 'amdgpu' to find a card to monitor

    returns the cardN name and hwmon directory for stats"""
    _card = None
    _hwmon_dir = None
    hwmon_names_glob = '/sys/class/drm/card*/device/hwmon/hwmon*/name'
    hwmon_names = glob.glob(hwmon_names_glob)
    for hwmon_name_file in hwmon_names:
        with open(hwmon_name_file, "r", encoding="utf-8") as _f:
            if _f.read().strip() == 'amdgpu':
                # found an amdgpu
                # note: if multiple are found, last will be used/watched
                # will be configurable in the future, may prompt
                _card = hwmon_name_file.split('/')[4]
                _hwmon_dir = path.dirname(hwmon_name_file)
    return _card, _hwmon_dir


# globals - card, hwmon directory, and statistic file paths derived from these
CARD, hwmon_dir = find_card()
card_dir = path.join("/sys/class/drm/", CARD)  # eg: /sys/class/drm/card0/
# ref: https://docs.kernel.org/gpu/amdgpu/thermal.html
SRC_FILES = {'pwr_limit': path.join(hwmon_dir, "power1_cap"),
             'pwr_average': path.join(hwmon_dir, "power1_average"),
             'pwr_cap': path.join(hwmon_dir, "power1_cap_max"),
             'pwr_default': path.join(hwmon_dir, "power1_cap_default"),
             'core_clock': path.join(hwmon_dir, "freq1_input"),
             'core_voltage': path.join(hwmon_dir, "in0_input"),
             'memory_clock': path.join(hwmon_dir, "freq2_input"),
             'busy_pct': path.join(card_dir, "device/gpu_busy_percent"),
             'temp_c': path.join(hwmon_dir, "temp1_input"),
             'fan_rpm': path.join(hwmon_dir, "fan1_input"),
             'fan_rpm_target': path.join(hwmon_dir, "fan1_target"),
             }
TEMP_FILES = {}
# determine temperature nodes, construct an empty dict to store them
temp_node_labels = glob.glob(path.join(hwmon_dir, "temp*_label"))
for temp_node_label_file in temp_node_labels:
    # determine the base node id, eg: temp1
    # construct the path to the file that will label it. ie: edge/junction
    temp_node_id = path.basename(temp_node_label_file).split('_')[0]
    temp_node_value_file = path.join(hwmon_dir, f"{temp_node_id}_input")
    with open(temp_node_label_file, 'r', encoding='utf-8') as _node:
        temp_node_name = _node.read().strip()
    # add the node name/type and the corresponding temp file to the dict
    TEMP_FILES[temp_node_name] = temp_node_value_file


def read_stat(file: str) -> str:
    """given `file`, return the contents"""
    with open(file, "r", encoding="utf-8") as _fh:
        data = _fh.read().strip()
        return data


def format_frequency(frequency_hz) -> str:
    """takes a frequency and formats it with an appropriate Hz suffix"""
    return (
        format_size(int(frequency_hz), binary=False)
        .replace("B", "Hz")
        .replace("bytes", "Hz")
    )


class LogScreen(Screen):
    """Creates a screen for the logging widget"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_log = TextLog(highlight=True, markup=True)

    def on_mount(self) -> None:
        """Event handler called when widget is first added
        On first display in this case."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(self.text_log)
        yield Footer()

#    def on_key(self, event: events.Key) -> None:
#        """Log/show key presses when the log window is open"""
#        self.text_log.write(event)


class GPUStatsWidget(Static):
    """The main stats widget."""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield ClockDisplay(classes="box")
        yield PowerDisplay(classes="box")
        yield MiscDisplay(classes="box")


class GPUStats(App):
    """Textual-based tool to show AMDGPU statistics."""

    # apply stylesheet
    CSS_PATH = 'amdgpu_stats.css'

    # initialize log screen
    SCREENS = {"logs": LogScreen()}

    # setup keybinds
    #    Binding("l", "push_screen('logs')", "Toggle logs", priority=True),
    BINDINGS = [
        Binding("c", "toggle_dark", "Toggle colors", priority=True),
        Binding("l", "toggle_log", "Toggle logs", priority=True),
        Binding("q", "quit_app", "Quit", priority=True)
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Container(GPUStatsWidget())
        self.update_log("[bold green]App started, logging begin!")
        self.update_log("[bold italic]Information sources:[/]")
        for metric, source in SRC_FILES.items():
            self.update_log(f'[bold]  {metric}:[/] {source}')
        for metric, source in TEMP_FILES.items():
            self.update_log(f'[bold]  {metric} temperature:[/] {source}')
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark
        self.update_log(f"Dark side: [bold]{self.dark}")

    def action_quit_app(self) -> None:
        """An action to quit the program"""
        message = "Exiting on user request"
        self.update_log(f"[bold]{message}")
        self.exit(message)

    def action_toggle_log(self) -> None:
        """Toggle between the main screen and the LogScreen."""
        if isinstance(self.screen, LogScreen):
            self.pop_screen()
        else:
            self.push_screen("logs")

    def update_log(self, message: str) -> None:
        """Update the TextLog widget with a new message."""
        log_screen = self.SCREENS["logs"]
        log_screen.text_log.write(message)


class MiscDisplay(Static):
    """A widget to display misc. GPU stats."""
    # construct the misc. stats dict; appended by discovered temperature nodes
    # used to make a 'reactive' object
    fan_stats = reactive({"fan_rpm": 0,
                          "fan_rpm_target": 0})
    temp_stats = reactive({})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_fan = None
        self.timer_temp = None

    def compose(self) -> ComposeResult:
        yield Horizontal(Label("[underline]Temperatures"),
                         Label("", classes="statvalue"))
        for temp_node in TEMP_FILES:
            # capitalize the first letter for display
            caption = temp_node[0].upper() + temp_node[1:]
            yield Horizontal(Label(f'  {caption}:',),
                             Label("", id="temp_" + temp_node, classes="statvalue"))
        yield Horizontal(Label("[underline]Fan RPM"),
                         Label("", classes="statvalue"))
        yield Horizontal(Label("  Current:",),
                         Label("", id="fan_rpm", classes="statvalue"))
        yield Horizontal(Label("  Target:",),
                         Label("", id="fan_rpm_target", classes="statvalue"))

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_fan = self.set_interval(1, self.update_fan_stats)
        self.timer_temp = self.set_interval(1, self.update_temp_stats)

    def update_fan_stats(self) -> None:
        """Method to update the 'fan' values to current measurements.

        Run by a timer created 'on_mount'"""
        val_update = {
                "fan_rpm": read_stat(SRC_FILES['fan_rpm']),
                "fan_rpm_target": read_stat(SRC_FILES['fan_rpm_target'])
        }
        self.fan_stats = val_update

    def update_temp_stats(self) -> None:
        """Method to update the 'temperature' values to current measurements.

        Run by a timer created 'on_mount'"""
        val_update = {}
        for temp_node, temp_file in TEMP_FILES.items():
            # iterate through the discovered temperature nodes
            # ... updating the dictionary with new stats
            _content = f'{int(read_stat(temp_file)) / 1000:.0f}C'
            val_update[temp_node] = _content
        self.temp_stats = val_update

    def watch_fan_stats(self, fan_stats: dict) -> None:
        """Called when the 'fan_stats' reactive attr changes.

         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#fan_rpm", Static).update(f"{fan_stats['fan_rpm']}")
        self.query_one("#fan_rpm_target", Static).update(f"{fan_stats['fan_rpm_target']}")

    def watch_temp_stats(self, temp_stats: dict) -> None:
        """Called when the temp_stats reactive attr changes, updates labels"""
        for temp_node in TEMP_FILES:
            # check first if the reactive object has been updated with keys
            if temp_node in temp_stats:
                stat_dict_item = temp_stats[temp_node]
                self.query_one("#temp_" + temp_node, Static).update(stat_dict_item)


class ClockDisplay(Static):
    """A widget to display GPU power stats."""
    core_vals = reactive({"sclk": 0, "mclk": 0, "voltage": 0, "util_pct": 0})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_clocks = None

    def compose(self) -> ComposeResult:
        yield Horizontal(Label("[underline]Clocks"),
                         Label("", classes="statvalue"))
        yield Horizontal(Label("  GPU core:",),
                         Label("", id="clk_core_val", classes="statvalue"))
        yield Horizontal(Label("  Memory:"),
                         Label("", id="clk_memory_val", classes="statvalue"))
        yield Horizontal(Label(""), Label("", classes="statvalue"))  # padding to split groups
        yield Horizontal(Label("[underline]Core"),
                         Label("", classes="statvalue"))
        yield Horizontal(Label("  Utilization:",),
                         Label("", id="util_pct", classes="statvalue"))
        yield Horizontal(Label("  Voltage:",),
                         Label("", id="clk_voltage_val", classes="statvalue"))

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_clocks = self.set_interval(1, self.update_core_vals)

    def update_core_vals(self) -> None:
        """Method to update GPU clock values to the current measurements.
        Run by a timer created 'on_mount'"""

        self.core_vals = {
            "sclk": format_frequency(read_stat(SRC_FILES['core_clock'])),
            "mclk": format_frequency(read_stat(SRC_FILES['memory_clock'])),
            "voltage": float(
                f"{int(read_stat(SRC_FILES['core_voltage'])) / 1000:.2f}"
            ),
            "util_pct": read_stat(SRC_FILES['busy_pct']),
        }

    def watch_core_vals(self, core_vals: dict) -> None:
        """Called when the clocks attribute changes
         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#clk_core_val", Static).update(f"{core_vals['sclk']}")
        self.query_one("#util_pct", Static).update(f"{core_vals['util_pct']}%")
        self.query_one("#clk_voltage_val", Static).update(f"{core_vals['voltage']}V")
        self.query_one("#clk_memory_val", Static).update(f"{core_vals['mclk']}")


class PowerDisplay(Static):
    """A widget to display GPU power stats."""

    micro_watts = reactive({"limit": 0,
                            "average": 0,
                            "capability": 0,
                            "default": 0})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_micro_watts = None

    def compose(self) -> ComposeResult:
        yield Horizontal(Label("[underline]Power"),
                         Label("", classes="statvalue"))
        yield Horizontal(Label("  Usage:",),
                         Label("", id="pwr_avg_val", classes="statvalue"))
        yield Horizontal(Label(""), Label("", classes="statvalue"))  # padding to split groups
        yield Horizontal(Label("[underline]Limits"),
                         Label("", classes="statvalue"))
        yield Horizontal(Label("  Configured:",),
                         Label("", id="pwr_lim_val", classes="statvalue"))
        yield Horizontal(Label("  Default:",),
                         Label("", id="pwr_def_val", classes="statvalue"))
        yield Horizontal(Label("  Board capability:",),
                         Label("", id="pwr_cap_val", classes="statvalue"))

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_micro_watts = self.set_interval(1, self.update_micro_watts)

    def update_micro_watts(self) -> None:
        """Method to update GPU power values to current measurements.

        Run by a timer created 'on_mount'"""
        self.micro_watts = {
            "limit": int(int(read_stat(SRC_FILES['pwr_limit'])) / 1000000),
            "average": int(int(read_stat(SRC_FILES['pwr_average'])) / 1000000),
            "capability": int(int(read_stat(SRC_FILES['pwr_cap'])) / 1000000),
            "default": int(int(read_stat(SRC_FILES['pwr_default'])) / 1000000),
        }

    def watch_micro_watts(self, micro_watts: dict) -> None:
        """Called when the micro_watts attributes change.
         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#pwr_avg_val", Static).update(f"{micro_watts['average']}W")
        self.query_one("#pwr_lim_val", Static).update(f"{micro_watts['limit']}W")
        self.query_one("#pwr_def_val", Static).update(f"{micro_watts['default']}W")
        self.query_one("#pwr_cap_val", Static).update(f"{micro_watts['capability']}W")


def tui() -> None:
    '''Spawns the textual UI only during CLI invocation / after argparse'''
    app = GPUStats()
    app.run()


def main():
    '''Main function, entrypoint for packaging'''
    # exit if AMDGPU not found, otherwise - proceed, assigning stat files
    if CARD is None:
        sys.exit('Could not find an AMD GPU, exiting.')
    tui()


if __name__ == "__main__":
    main()
