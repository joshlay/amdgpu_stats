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

from rich.text import Text
from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, TextLog, DataTable

from .utils import AMDGPU_CARDS, get_fan_rpm, get_power_stats, get_temp_stat, get_clock, get_gpu_usage, get_voltage
# pylint: disable=line-too-long

# rich markup reference:
#    https://rich.readthedocs.io/en/stable/markup.html


class LogScreen(Screen):
    """Creates a screen for the logging widget"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_log = TextLog(highlight=True, markup=True, name='log_gpu')

    def on_mount(self) -> None:
        """Event handler called when widget is first added
        On first display in this case."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield self.text_log
        yield Footer()

#    def on_key(self, event: events.Key) -> None:
#        """Log/show key presses when the log window is open"""
#        self.text_log.write(event)


class GPUStatsWidget(Static):
    """The main stats widget."""

    columns = ["card",
               "core clock",
               "memory clock",
               "utilization",
               "voltage",
               "power usage",
               "set limit",
               "default limit",
               "capability",
               "fan rpm",
               "edge temp",
               "junction temp",
               "memory temp"]
    timer_stats = None
    table = None
    table_needs_init = True
    data = {}

    def __init__(self, *args, cards=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Instance variables
        self.cards = cards

    async def on_mount(self) -> None:
        '''Fires when stats widget first shown'''
        self.table = self.query_one(DataTable)
        for column in self.columns:
            self.table.add_column(label=column, key=column)
        # self.table.add_columns(*self.columns)
        self.table_needs_init = True
        self.timer_stats = self.set_interval(1, self.get_stats)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        stats_table = DataTable(zebra_stripes=True, show_cursor=False, name='stats_table')
        yield stats_table
        self.update_log('[bold]App:[/] created stats table')

    def update_log(self, message: str) -> None:
        """Update the TextLog widget with a new message."""
        log_screen = AMDGPUStats.SCREENS["logs"]
        log_screen.text_log.write(message)

    def get_stats(self):
        '''Function to fetch stats / update the table'''
        for card in self.cards:
            power_stats = get_power_stats(card=card)
            self.data = {
                    "card": card,
                    "core clock": get_clock('core', card=card, format_freq=True),
                    "memory clock": get_clock('memory', card=card, format_freq=True),
                    "utilization": f'{get_gpu_usage(card=card)}%',
                    "voltage": f'{get_voltage(card=card)}V',
                    "power usage": f'{power_stats["average"]}W',
                    "set limit": f'{power_stats["limit"]}W',
                    "default limit": f'{power_stats["default"]}W',
                    "capability": f'{power_stats["capability"]}W',
                    "fan rpm": f'{get_fan_rpm(card=card)}',
                    "edge temp": f"{get_temp_stat(name='edge', card=card)}C",
                    "junction temp": f"{get_temp_stat(name='junction', card=card)}C",
                    "memory temp": f"{get_temp_stat(name='mem', card=card)}C"}
            # handle the table data appopriately
            # if needs populated anew or updated
            if self.table_needs_init:
                # Add rows for the first time
                # Adding styled and justified `Text` objects instead of plain strings.
                styled_row = [
                    Text(str(cell), style="italic", justify="right") for cell in self.data.values()
                ]
                self.table.add_row(*styled_row, key=card)
                hwmon_dir = AMDGPU_CARDS[card]
                self.update_log(f'[bold]stats:[/] added row for [bold green]{card}[/], info dir: {hwmon_dir}')
            else:
                # Update existing rows
                for column, value in self.data.items():
                    styled_cell = Text(str(value), style="italic", justify="right")
                    self.table.update_cell(card, column, styled_cell)
        if self.table_needs_init:
            # if this is the first time updating the table, mark it initialized
            self.table_needs_init = False
        self.table.refresh()


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
        Binding("l", "custom_log", "Logs"),
        Binding("s", "custom_screenshot", "Screenshot"),
        Binding("q", "quit", "Quit")
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        stats_widget = Container(GPUStatsWidget(cards=AMDGPU_CARDS,
                                                name="stats_widget"))
        yield stats_widget
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

    def action_custom_screenshot(self, screen_dir: str = '/tmp') -> None:
        """Action that fires when the user presses 's' for a screenshot"""
        # construct the screenshot elements + path
        timestamp = datetime.now().isoformat().replace(":", "_")
        screen_name = 'amdgpu_stats_' + timestamp + '.svg'
        screen_path = path.join(screen_dir, screen_name)
        self.action_screenshot(path=screen_dir, filename=screen_name)
        self.update_log(f'[bold]Screenshot taken: [italic]{screen_path}')

    def action_custom_log(self) -> None:
        """Toggle between the main screen and the LogScreen."""
        if isinstance(self.screen, LogScreen):
            self.pop_screen()
        else:
            self.push_screen("logs")

    def update_log(self, message: str) -> None:
        """Update the TextLog widget with a new message."""
        log_screen = self.SCREENS["logs"]
        log_screen.text_log.write(message)


def start() -> None:
    '''Spawns the textual UI only during CLI invocation / after argparse'''
    if len(AMDGPU_CARDS) > 0:
        app = AMDGPUStats(watch_css=True)
        app.run()
    else:
        sys.exit('Could not find an AMD GPU, exiting.')
