#!/usr/bin/python3
"""Pretty Textual-based stats for AMD GPUs

TODO: restore argparse / --card, in case detection fails.
      will require separating the hwmon finding tasks from 'find_card'

rich markup reference:
    https://rich.readthedocs.io/en/stable/markup.html
"""
import argparse
from os import path
import glob
import sys

# from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, TextLog, Label
from humanfriendly import format_size


def find_card():
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

    BINDINGS = [("l", "app.pop_screen", "Show/hide logs")]

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

    # determine the real path of the script, to load the stylesheet
    SCRIPT_PATH = path.dirname(path.realpath(__file__))
    CSS_PATH = path.join(SCRIPT_PATH, "stats.css")

    # initialize log screen
    SCREENS = {"logs": LogScreen()}

    # setup keybinds
    BINDINGS = [
        ("c", "toggle_dark", "Toggle colors"),
        ("l", "push_screen('logs')", "Show/hide logs"),
        ("q", "quit_app", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield Container(GPUStatsWidget())
        self.update_log("[bold green]App started, logging begin!")
        self.update_log("[bold italic]Information sources:[/]")
        for metric, source in src_files.items():
            self.update_log(f'[bold]  {metric}:[/] {source}')
        for metric, source in temp_files.items():
            self.update_log(f'[bold]  {metric} temperature:[/] {source}')

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark
        self.update_log(f"Dark side: [bold]{self.dark}")

    def action_quit_app(self) -> None:
        """An action to quit the program"""
        message = "Exiting on user request"
        self.update_log(f"[bold]{message}")
        self.exit(message)

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
        for temp_node in temp_files:
            # capitalize the first letter for display
            caption = temp_node[0].upper() + temp_node[1:]
            yield Horizontal(Label(f'[bold]{caption}[/] temp:',), Label("", id="temp_" + temp_node, classes="statvalue"))
        yield Horizontal(Label("[underline]Current[/] fan RPM:",), Label("", id="fan_rpm", classes="statvalue"))
        yield Horizontal(Label("[underline]Target[/] fan RPM:",), Label("", id="fan_rpm_target", classes="statvalue"))

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_fan = self.set_interval(interval, self.update_fan_stats)
        self.timer_temp = self.set_interval(interval, self.update_temp_stats)

    def update_fan_stats(self) -> None:
        """Method to update the 'fan' values to current measurements.

        Run by a timer created 'on_mount'"""
        val_update = {
                "fan_rpm": read_stat(src_files['fan_rpm']),
                "fan_rpm_target": read_stat(src_files['fan_rpm_target'])
        }
        self.fan_stats = val_update

    def update_temp_stats(self) -> None:
        """Method to update the 'temperature' values to current measurements.

        Run by a timer created 'on_mount'"""
        val_update = {}
        for temp_node, temp_file in temp_files.items():
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
        for temp_node in temp_files:
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
        yield Horizontal(Label("Core clock:",), Label("", id="clk_core_val", classes="statvalue"))
        yield Horizontal(Label("Utilization:",), Label("", id="util_pct", classes="statvalue"))
        yield Horizontal(Label("Core voltage:",), Label("", id="clk_voltage_val", classes="statvalue"))
        yield Horizontal(Label("Memory clock:"), Label("", id="clk_memory_val", classes="statvalue"))

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_clocks = self.set_interval(interval, self.update_core_vals)

    def update_core_vals(self) -> None:
        """Method to update GPU clock values to the current measurements.
        Run by a timer created 'on_mount'"""

        self.core_vals = {
            "sclk": format_frequency(read_stat(src_files['core_clock'])),
            "mclk": format_frequency(read_stat(src_files['memory_clock'])),
            "voltage": float(
                f"{int(read_stat(src_files['core_voltage'])) / 1000:.2f}"
            ),
            "util_pct": read_stat(src_files['busy_pct']),
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
        yield Horizontal(Label("Power usage:",),
                         Label("", id="pwr_avg_val", classes="statvalue"))
        yield Horizontal(Label("Power limit:",),
                         Label("", id="pwr_lim_val", classes="statvalue"))
        yield Horizontal(Label("[underline]Default[/] limit:",),
                         Label("", id="pwr_def_val", classes="statvalue"))
        yield Horizontal(Label("Board capability:",),
                         Label("", id="pwr_cap_val", classes="statvalue"))

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_micro_watts = self.set_interval(interval, self.update_micro_watts)

    def update_micro_watts(self) -> None:
        """Method to update GPU power values to current measurements.

        Run by a timer created 'on_mount'"""
        self.micro_watts = {
            "limit": int(int(read_stat(src_files['pwr_limit'])) / 1000000),
            "average": int(int(read_stat(src_files['pwr_average'])) / 1000000),
            "capability": int(int(read_stat(src_files['pwr_cap'])) / 1000000),
            "default": int(int(read_stat(src_files['pwr_default'])) / 1000000),
        }

    def watch_micro_watts(self, micro_watts: dict) -> None:
        """Called when the micro_watts attributes change.
         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#pwr_avg_val", Static).update(f"{micro_watts['average']}W")
        self.query_one("#pwr_lim_val", Static).update(f"{micro_watts['limit']}W")
        self.query_one("#pwr_def_val", Static).update(f"{micro_watts['default']}W")
        self.query_one("#pwr_cap_val", Static).update(f"{micro_watts['capability']}W")


if __name__ == "__main__":
    CARD, hwmon_dir = find_card()
    # do the argparse dance
    p = argparse.ArgumentParser(
            # show the value for defaults in '-h/--help'
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="Show some basic AMD GPU stats -- tested on RX6xxx series",
            )
#    p.add_argument(
#            "-c",
#            "--card",
#            type=str,
#            default=AUTO_CARD,
#            help="The GPU to inspect, see 'ls -lad /sys/class/drm/card*'",
#            )
    p.add_argument(
            "-i",
            "--interval",
            type=float,
            default=1.0,
            help="The delay (in seconds) between polling for data",
            )
    args = p.parse_args()
    interval = args.interval
#    CARD = args.card

    # detect AMD GPU, exit if unfound
    if CARD is None:
        sys.exit('Could not find an AMD GPU, exiting.')

    card_dir = path.join("/sys/class/drm/", CARD)  # eg: /sys/class/drm/card0/
    # ref: https://docs.kernel.org/gpu/amdgpu/thermal.html
    src_files = {'pwr_limit': path.join(hwmon_dir, "power1_cap"),
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
    # notes:
    #   assumptions are made that freq{1,2}_input files are sclk/mclk
    #   contents of files named freq{1,2}_label can determine this reliably
    #   similarly:
    #      'in0_input' has a peer named 'in0_label'
    #      should contain 'vddgfx' to indicate core voltage
    #   TODO: implement ^
    #
    # determine temperature nodes, construct an empty dict to store them
    temp_files = {}
    temp_node_labels = glob.glob(path.join(hwmon_dir, "temp*_label"))
    for temp_node_label_file in temp_node_labels:
        # determine the base node id, eg: temp1
        # construct the path to the file that will label it. ie: edge/junction
        temp_node_id = path.basename(temp_node_label_file).split('_')[0]
        temp_node_value_file = path.join(hwmon_dir, f"{temp_node_id}_input")
        with open(temp_node_label_file, 'r', encoding='utf-8') as _node:
            temp_node_name = _node.read().strip()
        print(f'found temp: {temp_node_name} (id: {temp_node_id})')
        # add the node name/type and the corresponding temp file to the dict
        temp_files[temp_node_name] = temp_node_value_file

    app = GPUStats()
    app.run()
