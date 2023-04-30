"""
tui.py

This file provides the user interface of `amdgpu-stats`

Can be used as a way to monitor GPU(s) in your terminal, or inform other utilities.

Classes:
    - GPUStats: the object for the _Application_, instantiated at runtime
    - GPUStatsWidget: the primary container for the three stat widgets:
        - MiscDisplay
        - ClockDisplay
        - PowerDisplay
    - LogScreen: Second screen with the logging widget, header, and footer

Functions:
    - start: Creates the 'App' and renders the TUI using the classes above
"""
# disable superfluouos linting
# pylint: disable=line-too-long
import sys
from datetime import datetime
from os import path

from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, TextLog, Label

from .utils import AMDGPU_CARDS, format_frequency, get_core_stats, get_fan_rpm, get_fan_target, get_power_stats, get_temp_stats  # pylint: disable=line-too-long

# rich markup reference:
#    https://rich.readthedocs.io/en/stable/markup.html


class LogScreen(Screen):
    """Creates a screen for the logging widget"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_log = TextLog(highlight=True, markup=True)

    def on_mount(self) -> None:
        """Event handler called when widget is first added
        On first display in this case."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(self.text_log)
        yield Footer()

#    def on_key(self, event: events.Key) -> None:
#        """Log/show key presses when the log window is open"""
#        self.text_log.write(event)


class GPUStatsWidget(Static):
    """The main stats widget."""

    def __init__(self, *args, card=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Instance variables
        self.card = card
        self.hwmon_dir = AMDGPU_CARDS[self.card]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield ClockDisplay(classes="box", card=self.card, hwmon_dir=self.hwmon_dir)
        yield PowerDisplay(classes="box", card=self.card, hwmon_dir=self.hwmon_dir)
        yield MiscDisplay(classes="box", card=self.card)
        _msg = f'''[bold]App:[/] creating stat widgets for [green]{self.card}[/], stats directory: {self.hwmon_dir}'''
        self.update_log(_msg)

    def update_log(self, message: str) -> None:
        """Update the TextLog widget with a new message."""
        log_screen = AMDGPUStats.SCREENS["logs"]
        log_screen.text_log.write(message)


class AMDGPUStats(App):
    """Textual-based tool to show AMDGPU statistics."""

    # apply stylesheet
    CSS_PATH = 'style.css'

    # initialize log screen
    SCREENS = {"logs": LogScreen()}

    # title the app after the card
    # TITLE = 'GPUStats - ' + CARD

    # setup keybinds
    #    Binding("l", "push_screen('logs')", "Toggle logs", priority=True),
    BINDINGS = [
        Binding("c", "custom_dark", "Colors"),
        Binding("l", "toggle_log", "Logs"),
        Binding("s", "screenshot_wrapper", "Screenshot"),
        Binding("q", "quit", "Quit")
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        for card in AMDGPU_CARDS:
            stat_widget_name = "stats_" + card
            yield Label(card, expand=True, classes='widgetheader')
            widget = Container(GPUStatsWidget(card=card, id=stat_widget_name))
            yield widget
        self.update_log("[bold green]App started, logging begin!")
        self.update_log(f"[bold]Discovered AMD GPUs:[/] {list(AMDGPU_CARDS)}")
        # nice-to-have: account for not storing these in dicts, but resolved in funcs
        # for metric, source in SRC_FILES.items():
        #    self.update_log(f'[bold]  {metric}:[/] {source}')
        # for metric, source in TEMP_FILES.items():
        #    self.update_log(f'[bold]  {metric} temperature:[/] {source}')
        yield Footer()

    async def action_custom_dark(self) -> None:
        """An action to toggle dark mode.

        Wraps 'action_toggle_dark' with logging and a refresh"""
        self.dark = not self.dark
        self.update_log(f"[bold]Dark side: [italic]{self.dark}")
        self.refresh()
        # self.dark = not self.dark

    def action_screenshot_wrapper(self, screen_dir: str = '/tmp') -> None:
        """Action that fires when the user presses 's' for a screenshot"""
        # construct the screenshot elements + path
        timestamp = datetime.now().isoformat().replace(":", "_")
        screen_name = 'amdgpu_stats_' + timestamp + '.svg'
        screen_path = path.join(screen_dir, screen_name)
        self.action_screenshot(path=screen_dir, filename=screen_name)
        self.update_log(f'[bold]Screenshot taken: [italic]{screen_path}')

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
    fan_rpm = reactive(0)
    fan_rpm_target = reactive(0)
    # do some dancing to craft the UI; initialize the reactive obj with data
    # dynamic object for temperature updates
    # populated / looped in '__init__' to get proper labels
    temp_stats = reactive({})
    # default to 'not composed', once labels are made - become true
    # avoids a race condition between discovering temperature nodes/stats
    # ... and making labels for them
    composed = False

    def __init__(self, card: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_misc = None
        self.card = card
        self.temp_stats = get_temp_stats(self.card)

    def compose(self) -> ComposeResult:
        yield Horizontal(Label("[underline]Temperatures"),
                         Label("", classes="statvalue"))
        for temp_node in self.temp_stats:
            # capitalize the first letter for display
            caption = temp_node[0].upper() + temp_node[1:]
            yield Horizontal(Label(f' {caption}:',),
                             Label("", id="temp_" + temp_node, classes="statvalue"))
        # padding to split groups
        yield Horizontal()
        yield Horizontal(Label("[underline]Fan RPM"),
                         Label("", classes="statvalue"))
        yield Horizontal(Label(" Current:",),
                         Label("", id="fan_rpm", classes="statvalue"))
        yield Horizontal(Label(" Target:",),
                         Label("", id="fan_rpm_target", classes="statvalue"))
        self.composed = True

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_misc = self.set_interval(1, self.update_misc_stats)

    def update_misc_stats(self) -> None:
        """Method to update the temp/fan values to current measurements.

        Run by a timer created 'on_mount'"""
        self.fan_rpm = get_fan_rpm(self.card)
        self.fan_rpm_target = get_fan_target(self.card)
        self.temp_stats = get_temp_stats(self.card)

    def watch_fan_rpm(self, fan_rpm: int) -> None:
        """Called when the 'fan_rpm' reactive attr changes.

         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#fan_rpm", Static).update(f"{fan_rpm}")

    def watch_fan_rpm_target(self, fan_rpm_target: int) -> None:
        """Called when the 'fan_rpm_target' reactive attr changes.

         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#fan_rpm_target", Static).update(f"{fan_rpm_target}")

    def watch_temp_stats(self, temp_stats: dict) -> None:
        """Called when the temp_stats reactive attr changes, updates labels"""
        # try to avoid racing
        if not self.composed:
            return
        for temp_node in temp_stats:
            item_val = self.temp_stats[temp_node]
            self.query_one("#temp_" + temp_node, Static).update(f'{item_val}C')


class ClockDisplay(Static):
    """A widget to display GPU power stats."""
    core_vals = reactive({"sclk": 0, "mclk": 0, "voltage": 0, "util_pct": 0})

    def __init__(self, card: str, hwmon_dir: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_clocks = None
        self.card = card
        self.hwmon_dir = hwmon_dir

    def compose(self) -> ComposeResult:
        yield Horizontal(Label("[underline]Performance"),
                         Label("", classes="statvalue"))
        yield Horizontal(Label(" Core clock:",),
                         Label("", id="clk_core_val", classes="statvalue"))
        yield Horizontal(Label(" Memory clock:"),
                         Label("", id="clk_memory_val", classes="statvalue"))
        yield Horizontal(Label(" Utilization:",),
                         Label("", id="util_pct", classes="statvalue"))
        yield Horizontal(Label(" Voltage:",),
                         Label("", id="clk_voltage_val", classes="statvalue"))
        # padding underneath, don't let them space out vertically
        yield Horizontal()
        yield Horizontal()
        yield Horizontal()
        yield Horizontal()

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_clocks = self.set_interval(1, self.update_core_vals)

    def update_core_vals(self) -> None:
        """Method to update GPU clock values to the current measurements.
        Run by a timer created 'on_mount'"""
        self.core_vals = get_core_stats(self.card)

    def watch_core_vals(self, core_vals: dict) -> None:
        """Called when the clocks attribute changes
         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#clk_core_val",
                       Static).update(f"{format_frequency(core_vals['sclk'])}")
        self.query_one("#util_pct",
                       Static).update(f"{core_vals['util_pct']}%")
        self.query_one("#clk_voltage_val",
                       Static).update(f"{core_vals['voltage']}V")
        self.query_one("#clk_memory_val",
                       Static).update(f"{format_frequency(core_vals['mclk'])}")


class PowerDisplay(Static):
    """A widget to display GPU power stats."""

    watts = reactive({"limit": 0,
                      "limit_pct": 0,
                      "average": 0,
                      "capability": 0,
                      "default": 0})

    def __init__(self, card: str, hwmon_dir: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer_watts = None
        self.card = card
        self.hwmon_dir = hwmon_dir

    def compose(self) -> ComposeResult:
        yield Horizontal(Label("[underline]Power"),
                         Label("", classes="statvalue"))
        yield Horizontal(Label(" Usage:",),
                         Label("", id="pwr_avg_val", classes="statvalue"))
        yield Horizontal(Label(" Set Limit:",),
                         Label("", id="pwr_lim_val", classes="statvalue"))
        yield Horizontal(Label(" Default Limit:",),
                         Label("", id="pwr_def_val", classes="statvalue"))
        yield Horizontal(Label(" Capability:",),
                         Label("", id="pwr_cap_val", classes="statvalue"))
        yield Horizontal()
        yield Horizontal()
        yield Horizontal()
        yield Horizontal()

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.timer_watts = self.set_interval(1, self.update_watts)

    def update_watts(self) -> None:
        """Method to update GPU power values to current measurements.

        Run by a timer created 'on_mount'"""
        self.watts = get_power_stats(self.card)

    def watch_watts(self, watts: dict) -> None:
        """Called when the 'watts' reactive attribute (var) changes.
         - Updates label values
         - Casting inputs to string to avoid type problems w/ int/None"""
        self.query_one("#pwr_avg_val",
                       Static).update(f"{watts['limit_pct']}%, {watts['average']}W")
        self.query_one("#pwr_lim_val",
                       Static).update(f"{watts['limit']}W")
        self.query_one("#pwr_def_val",
                       Static).update(f"{watts['default']}W")
        self.query_one("#pwr_cap_val",
                       Static).update(f"{watts['capability']}W")


def start() -> None:
    '''Spawns the textual UI only during CLI invocation / after argparse'''
    if len(AMDGPU_CARDS) > 0:
        app = AMDGPUStats(watch_css=True)
        app.run()
    else:
        sys.exit('Could not find an AMD GPU, exiting.')
