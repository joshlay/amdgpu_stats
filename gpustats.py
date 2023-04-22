#!/usr/bin/python3
"""Pretty Textual-based stats for AMD GPUs

TODO: restore argparse / --card, in case detection fails

rich markup reference:
    https://rich.readthedocs.io/en/stable/markup.html
"""
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

    # for bringing in the log writing method
    misc_stats = reactive({"util_pct": 0,
                           "temp": 0,
                           "fan_rpm": 0,
                           "fan_rpm_target": 0})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_misc = None

    def compose(self) -> ComposeResult:
        yield Horizontal(Label("Utilization:",), Label("", id="util_pct", classes="statvalue"))
        yield Horizontal(Label("Temperature:",), Label("", id="temp_c", classes="statvalue"))
        yield Horizontal(Label("[underline]Current[/] fan RPM:",), Label("", id="fan_rpm", classes="statvalue"))
        yield Horizontal(Label("[underline]Target[/] fan RPM:",), Label("", id="fan_rpm_target", classes="statvalue"))

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_misc = self.set_interval(1, self.update_misc_stats)

    def update_misc_stats(self) -> None:
        """Method to update the 'misc' values to current measurements.
        Utilization % and temperature (C)

        Run by a timer created 'on_mount'"""
        self.misc_stats = {
            "util_pct": read_stat(src_files['busy_pct']),
            "temp": int(int(read_stat(src_files['temp_c'])) / 1000),
            "fan_rpm": read_stat(src_files['fan_rpm']),
            "fan_rpm_target": read_stat(src_files['fan_rpm_target'])
        }

    def watch_misc_stats(self, misc_stats: dict) -> None:
        """Called when the clocks attribute changes.
         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#util_pct", Static).update(f"{misc_stats['util_pct']}%")
        self.query_one("#temp_c", Static).update(f"{misc_stats['temp']}C")
        self.query_one("#fan_rpm", Static).update(f"{misc_stats['fan_rpm']}")
        self.query_one("#fan_rpm_target", Static).update(f"{misc_stats['fan_rpm_target']}")


class ClockDisplay(Static):
    """A widget to display GPU power stats."""
    clocks = reactive({"sclk": 0, "mclk": 0, "core_voltage": 0})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_clocks = None

    def compose(self) -> ComposeResult:
        yield Horizontal(Label("Core clock:",), Label("", id="clk_core_val", classes="statvalue"))
        yield Horizontal(Label("Core voltage:",), Label("", id="clk_voltage_val", classes="statvalue"))
        yield Horizontal(Label("Memory clock:"), Label("", id="clk_memory_val", classes="statvalue"))

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_clocks = self.set_interval(1, self.update_clocks)

    def update_clocks(self) -> None:
        """Method to update GPU clock values to the current measurements.
        Run by a timer created 'on_mount'"""

        self.clocks = {
            "sclk": format_frequency(read_stat(src_files['core_clock'])),
            "mclk": format_frequency(read_stat(src_files['memory_clock'])),
            "core_voltage": float(
                f"{int(read_stat(src_files['core_voltage'])) / 1000:.2f}"
            ),
        }

    def watch_clocks(self, clocks: dict) -> None:
        """Called when the clocks attribute changes
         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#clk_core_val", Static).update(f"{clocks['sclk']}")
        self.query_one("#clk_voltage_val", Static).update(f"{clocks['core_voltage']}V")
        self.query_one("#clk_memory_val", Static).update(f"{clocks['mclk']}")


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
        self.timer_micro_watts = self.set_interval(1, self.update_micro_watts)

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
    # detect AMD GPU, exit if unfound
    CARD, hwmon_dir = find_card()
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
    app = GPUStats()
    app.run()
