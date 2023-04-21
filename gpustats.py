#!/usr/bin/python3
"""Pretty Textual-based stats for AMD GPUs

TODO: restore argparse / --card, in case detection fails"""
from os import path, listdir
import glob
import re
import sys

# from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, TextLog, Label
from humanfriendly import format_size


def find_card():
    """searches /sys/class/drm/*/status for connected cards

    TODO: move the name/amdgpu check from find_hwmon, here
      if none found, return None.
      script should exit: reporting no AMD GPUs found"""
    _card = False
    status_path = "/sys/class/drm/*/status"
    files = glob.glob(status_path)
    for file in files:
        with open(file, "r", encoding="utf-8") as _f:
            for line in _f:
                if re.search(r"^connected", line):
                    # found a connected card/display
                    _card = path.basename(path.dirname(file)).split("-")[0]
    return _card


def find_hwmon(card):
    """for the provided `card`, find the hwmon path that provides stats"""
    hwmon_src = path.join("/sys/class/drm/", card, "device/hwmon/")
    for hwmon_candidate in listdir(hwmon_src):
        name_file = path.join(hwmon_src, hwmon_candidate, "name")
        # check if the name file exists
        if path.exists(name_file):
            # read the contents of the name file
            with open(name_file, "r", encoding="utf-8") as name_fh:
                name = name_fh.read().strip()

            # check if the name matches the desired GPU
            if name == "amdgpu":
                # found the correct hwmon directory
                # print(f'found amdgpu hwmon: {hwmon_candidate}')
                hwmon_path = path.join(hwmon_src, hwmon_candidate)
                return hwmon_path
    # if nothing found, return None
    return None


def read_stat(file):
    """given `file`, return the contents"""
    with open(file, "r", encoding="utf-8") as _fh:
        data = _fh.read().strip()
        return data


def format_frequency(frequency_hz):
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
    misc_stats = reactive({"util_pct": 0, "temp": 0})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_misc = None

    def compose(self) -> ComposeResult:
        yield Label("Misc:", classes="statlabel")

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_misc = self.set_interval(1, self.update_misc_stats)

    def update_misc_stats(self) -> None:
        """Method to update the 'misc' values to current measurements.
        Utilization % and temperature (C)"""
        self.misc_stats = {
            "util_pct": read_stat(src_files['busy_pct']),
            "temp": int(int(read_stat(src_files['temp_c'])) / 1000),
        }

    def watch_misc_stats(self, misc_stats: dict) -> None:
        """Called when the clocks attribute changes."""
        output = f"""Temp:    {misc_stats['temp']}C
Util:    {misc_stats['util_pct']}%"""
        self.update(output)


class ClockDisplay(Static):
    """A widget to display GPU power stats."""

    clocks = reactive({"sclk": 0, "mclk": 0, "core_voltage": 0})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_clocks = None

    def compose(self) -> ComposeResult:
        yield Label("Clocks:", classes="statlabel")

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_clocks = self.set_interval(1, self.update_clocks)

    def update_clocks(self) -> None:
        """Method to update GPU clock values to the current measurements."""
        self.clocks = {
            "sclk": format_frequency(read_stat(src_files['core_clock'])),
            "mclk": format_frequency(read_stat(src_files['memory_clock'])),
            "core_voltage": float(
                f"{int(read_stat(src_files['core_voltage'])) / 1000:.2f}"
            ),
        }

    def watch_clocks(self, clocks: dict) -> None:
        """Called when the clocks attribute changes."""
        output = f"""Core:      {clocks['sclk']} @ {clocks['core_voltage']}V
Memory:    {clocks['mclk']}"""
        self.update(output)


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
        yield Label("Power:", classes="statlabel")

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_micro_watts = self.set_interval(1, self.update_micro_watts)

    def update_micro_watts(self) -> None:
        """Method to update GPU power values to current measurements."""
        self.micro_watts = {
            "limit": int(int(read_stat(src_files['pwr_limit'])) / 1000000),
            "average": int(int(read_stat(src_files['pwr_average'])) / 1000000),
            "capability": int(int(read_stat(src_files['pwr_cap'])) / 1000000),
            "default": int(int(read_stat(src_files['pwr_default'])) / 1000000),
        }

    def watch_micro_watts(self, micro_watts: dict) -> None:
        """Called when the micro_watts attributes change."""
        output = f"""Using:        {micro_watts['average']}W
Set limit:    {micro_watts['limit']}W
Default:      {micro_watts['default']}W
Board cap:    {micro_watts['capability']}W"""
        self.update(output)


if __name__ == "__main__":
    CARD = find_card()
    card_dir = path.join("/sys/class/drm/", CARD)  # eg: /sys/class/drm/card0/
    hwmon_dir = find_hwmon(CARD)
    if hwmon_dir is None:
        sys.exit(
            """Could not determine hwmon, exiting.
    Consider '--card', perhaps {CARD} is incorrect"""
        )
    src_files = {'pwr_limit': path.join(hwmon_dir, "power1_cap"),
                 'pwr_average': path.join(hwmon_dir, "power1_average"),
                 'pwr_cap': path.join(hwmon_dir, "power1_cap_max"),
                 'pwr_default': path.join(hwmon_dir, "power1_cap_default"),
                 'core_clock': path.join(hwmon_dir, "freq1_input"),
                 'core_voltage': path.join(hwmon_dir, "in0_input"),
                 'memory_clock': path.join(hwmon_dir, "freq2_input"),
                 'busy_pct': path.join(card_dir, "device/gpu_busy_percent"),
                 'temp_c': path.join(hwmon_dir, "temp1_input")}
    app = GPUStats()
    app.run()
