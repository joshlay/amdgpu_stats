"""
tui.py

This file provides the user interface of `amdgpu-stats`

Can be used as a way to monitor GPU(s) in your terminal, or inform other utilities.

Classes:
    - GPUStats: the object for the _Application_, instantiated at runtime
    - GPUStatsWidget: the primary container for the tabbed content; stats table / logs

Functions:
    - start: Creates the 'App' and renders the TUI using the classes above
"""
# disable superfluouos linting
# pylint: disable=line-too-long
import sys
from datetime import datetime

from rich.text import Text
from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import (
        Header, Footer, Static, TextLog, DataTable, TabbedContent
        )

from .utils import (
        AMDGPU_CARDS,
        get_fan_rpm,
        get_power_stats,
        get_temp_stat,
        get_clock,
        get_gpu_usage,
        get_voltage
)
# rich markup reference:
#    https://rich.readthedocs.io/en/stable/markup.html


class Notification(Static):
    '''Self-removing notification widget'''

    def on_mount(self) -> None:
        '''On the creation/display of the notification...

        Creates a timer to remove itself in 3 seconds'''
        self.set_timer(3, self.remove)

    def on_click(self) -> None:
        '''Fires when notification is clicked, removes the widget'''
        self.remove()


class GPUStatsWidget(Static):
    """The main stats widget."""

    columns = ["Card",
               "Core clock",
               "Memory clock",
               "Utilization",
               "Voltage",
               "Power",
               "[italic]Limit",
               "[italic]Default",
               "[italic]Capability",
               "Fan RPM",
               "Edge temp",
               "Junction temp",
               "Memory temp"]
    timer_stats = None
    text_log = None
    stats_table = None
    table = None
    table_needs_init = True
    data = {}

    def __init__(self, *args, cards=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cards = cards
        self.text_log = TextLog(highlight=True, markup=True, name='log_gpu', classes='logs')
        self.stats_table = DataTable(zebra_stripes=True, show_cursor=False, name='stats_table', classes='stat_table')

    async def on_mount(self) -> None:
        '''Fires when stats widget first shown'''
        self.table = self.query_one(DataTable)
        # construct the table columns
        for column in self.columns:
            self.table.add_column(label=column, key=column)
        # mark the table as needing initialization (with rows)
        self.table_needs_init = True
        # do a one-off stat collection, populate table before the interval
        if self.table_needs_init:
            self.get_stats()
        # stand up the stat-collecting interval, once per second
        self.timer_stats = self.set_interval(1, self.get_stats)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        # Add the TabbedContent widget
        with TabbedContent("Stats", "Logs"):
            yield self.stats_table
            yield self.text_log
        self.update_log("[bold green]App started, logging begin!")
        self.update_log(f"[bold]Discovered AMD GPUs: [/]{list(AMDGPU_CARDS)}")
        self.update_log('[bold]App: [/]created stats table')

    def update_log(self, message: str) -> None:
        """Update the TextLog widget with a new message."""
        self.text_log.write(message)

    def get_stats(self):
        '''Function to fetch stats / update the table'''
        for card in self.cards:
            power_stats = get_power_stats(card=card)
            # annoyingly, must retain the styling used w/ the cols above
            # otherwise stats won't update
            #   noticed when fiddling 'style' below between new/update 'Text'
            self.data = {
                    "Card": card,
                    "Core clock": get_clock('core', card=card, format_freq=True),
                    "Memory clock": get_clock('memory', card=card, format_freq=True),
                    "Utilization": f'{get_gpu_usage(card=card)}%',
                    "Voltage": f'{get_voltage(card=card)}V',
                    "Power": f'{power_stats["average"]}W',
                    "[italic]Limit": f'{power_stats["limit"]}W',
                    "[italic]Default": f'{power_stats["default"]}W',
                    "[italic]Capability": f'{power_stats["capability"]}W',
                    "Fan RPM": f'{get_fan_rpm(card=card)}',
                    "Edge temp": f"{get_temp_stat(name='edge', card=card)}C",
                    "Junction temp": f"{get_temp_stat(name='junction', card=card)}C",
                    "Memory temp": f"{get_temp_stat(name='mem', card=card)}C"}
            # handle the table data appopriately
            # if needs populated anew or updated
            if self.table_needs_init:
                # Add rows for the first time
                # Adding right-justified `Text` objects instead of plain strings
                styled_row = [
                    Text(str(cell), style="normal", justify="right") for cell in self.data.values()
                ]
                self.table.add_row(*styled_row, key=card)
                hwmon_dir = AMDGPU_CARDS[card]
                self.update_log(f"[bold]Table: [/]added row for '{card}', info dir: '{hwmon_dir}'")
            else:
                # Update existing rows, retaining styling/justification
                for column, value in self.data.items():
                    styled_cell = Text(str(value), style="normal", justify="right")
                    self.table.update_cell(card, column, styled_cell)
        if self.table_needs_init:
            # if this is the first time updating the table, mark it initialized
            self.table_needs_init = False
        self.table.refresh()


class AMDGPUStats(App):
    """Textual-based tool to show AMDGPU statistics."""

    # apply stylesheet
    CSS_PATH = 'style.css'

    # setup keybinds
    BINDINGS = [
        Binding("c", "custom_dark", "Colors"),
        Binding("l", "custom_log", "Logs"),
        Binding("s", "custom_screenshot", "Screenshot"),
        Binding("q", "quit", "Quit")
    ]
    stats_widget = GPUStatsWidget(cards=AMDGPU_CARDS,
                                  name="stats_widget")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Footer()
        yield Container(self.stats_widget)

    def action_custom_dark(self) -> None:
        """An action to toggle dark mode.

        Wraps 'action_toggle_dark' with logging and a refresh"""
        self.app.dark = not self.app.dark
        self.update_log(f"[bold]Dark side: [italic]{self.app.dark}")

    def action_custom_screenshot(self, screen_dir: str = '/tmp') -> None:
        """Action that fires when the user presses 's' for a screenshot"""
        # construct the screenshot elements: name (w/ ISO timestamp) + path
        timestamp = datetime.now().isoformat().replace(":", "_")
        screen_name = 'amdgpu_stats_' + timestamp + '.svg'
        # take the screenshot, recording the path for logging/notification
        outpath = self.save_screenshot(path=screen_dir, filename=screen_name)
        # construct the log/notification message, then show it
        message = Text.assemble("Screenshot saved to ", (f"'{outpath}'", "bold"))
        self.screen.mount(Notification(message))
        self.update_log(message)

    def action_custom_log(self) -> None:
        """Toggle between the main screen and the LogScreen."""
        active = self.query_one(TabbedContent).active
        # if the second tab (logs), go to first
        if active == "tab-2":
            self.query_one(TabbedContent).active = 'tab-1'
        else:
            # otherwise, go to logs
            self.query_one(TabbedContent).active = 'tab-2'

    def update_log(self, message: str) -> None:
        """Update the TextLog widget with a new message."""
        log = self.stats_widget.text_log
        log.write(message)


def start() -> None:
    '''Spawns the textual UI only during CLI invocation / after argparse'''
    if len(AMDGPU_CARDS) > 0:
        app = AMDGPUStats(watch_css=True)
        app.run()
    else:
        sys.exit('Could not find an AMD GPU, exiting.')
