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
from datetime import datetime
from typing import Optional

from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import (
        Header,
        Footer,
        Static,
        TextLog,
        DataTable,
        TabbedContent,
        TabPane,
        )

from .utils import (
        AMDGPU_CARDS,
        get_fan_rpm,
        get_power_stats,
        get_temp_stat,
        get_clock,
        get_gpu_usage,
        get_voltage,
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

    def get_column_data_mapping(self, card: Optional[str] = None) -> dict:
        '''Returns a dictionary of stats

        Columns are derived from keys, and values provide measurements
        *Measurements require `card`*'''
        if card is None:
            return {
                "Card": "",
                "Core clock": "",
                "Memory clock": "",
                "Utilization": "",
                "Voltage": "",
                "Power": "",
                "[italic]Limit": "",
                "[italic]Default": "",
                "[italic]Capability": "",
                "Fan RPM": "",
                "Edge temp": "",
                "Junction temp": "",
                "Memory temp": ""
            }
        return {
            "Card": card,
            "Core clock": get_clock('core', card=card, format_freq=True),
            "Memory clock": get_clock('memory', card=card, format_freq=True),
            "Utilization": f'{get_gpu_usage(card=card)}%',
            "Voltage": f'{get_voltage(card=card)}V',
            "Power": f'{get_power_stats(card=card)["average"]}W',
            "[italic]Limit": f'{get_power_stats(card=card)["limit"]}W',
            "[italic]Default": f'{get_power_stats(card=card)["default"]}W',
            "[italic]Capability": f'{get_power_stats(card=card)["capability"]}W',
            "Fan RPM": f'{get_fan_rpm(card=card)}',
            "Edge temp": f"{get_temp_stat(name='edge', card=card)}C",
            "Junction temp": f"{get_temp_stat(name='junction', card=card)}C",
            "Memory temp": f"{get_temp_stat(name='mem', card=card)}C"
        }

    # initialize empty/default instance vars and objects
    data = {}
    stats_table = None
    tabbed_container = None
    text_log = None
    timer_stats = None
    # mark the table as needing initialization (with rows)
    table_needs_init = True

    def __init__(self, *args, cards=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cards = cards
        self.text_log = TextLog(highlight=True,
                                markup=True,
                                name='log_gpu',
                                classes='logs')
        self.stats_table = DataTable(zebra_stripes=True,
                                     show_cursor=True,
                                     name='stats_table',
                                     classes='stat_table')
        self.tabbed_container = TabbedContent()

    def on_mount(self) -> None:
        '''Fires when stats widget 'mounted', behaves like on first showing'''
        self.update_log("[bold green]App started, logging begin!")
        self.update_log(f"[bold]Discovered AMD GPUs: [/]{list(AMDGPU_CARDS)}")
        # construct the table columns
        columns = list(self.get_column_data_mapping(None).keys())
        self.update_log('[bold]Stats table columns:')
        for column in columns:
            self.stats_table.add_column(label=column, key=column)
            self.update_log(f'  - "{column}"')
        # do a one-off stat collection, populate table before the interval
        self.get_stats()
        # stand up the stat-collecting interval, twice per second
        self.timer_stats = self.set_interval(0.5, self.get_stats)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with self.tabbed_container:
            with TabPane("Stats", id="tab_stats"):
                yield self.stats_table
            with TabPane("Logs", id="tab_logs"):
                yield self.text_log

    def update_log(self, message: str) -> None:
        """Update the TextLog widget with a new message."""
        self.text_log.write(message)

    @work(exclusive=True)
    async def get_stats(self):
        '''Function to fetch stats / update the table for each AMD GPU found'''
        for card in self.cards:
            self.data = self.get_column_data_mapping(card)
            # handle the table data appopriately
            # if needs populated anew or updated
            if self.table_needs_init:
                # Add rows for the first time
                # Adding right-justified `Text` objects instead of plain strings
                styled_row = [
                    Text(str(cell), style="normal", justify="right") for cell in self.data.values()
                ]
                self.stats_table.add_row(*styled_row, key=card)
                hwmon_dir = AMDGPU_CARDS[card]
                self.update_log(f"[bold]Stats table: [/]added row for '{card}', info dir: '{hwmon_dir}'")
            else:
                # Update existing rows, retaining styling/justification
                for column, value in self.data.items():
                    styled_cell = Text(str(value), style="normal", justify="right")
                    self.stats_table.update_cell(card, column, styled_cell)
        if self.table_needs_init:
            # if this is the first time updating the table, mark it initialized
            self.table_needs_init = False


class app(App):  # pylint: disable=invalid-name
    """Textual-based tool to show AMDGPU statistics."""

    # apply stylesheet; this is watched/dynamically reloaded
    # can be edited (in installation dir) and seen live
    CSS_PATH = 'style.css'

    # set the title - same as the class, but with spaces
    TITLE = 'AMD GPU Stats'
    SUB_TITLE = ''

    # setup keybinds
    BINDINGS = [
        Binding("c", "custom_dark", "Colors"),
        Binding("t", "custom_tab", "Tab switch"),
        Binding("s", "custom_screenshot", "Screenshot"),
        Binding("q", "quit", "Quit")
    ]

    # create an instance of the stats widget with all cards
    stats_widget = GPUStatsWidget(cards=AMDGPU_CARDS,
                                  name="stats_widget")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Container(self.stats_widget)
        yield Footer()

    @work(exclusive=True)
    async def action_custom_dark(self) -> None:
        """An action to toggle dark mode.

        Wraps 'action_toggle_dark' with our logging"""
        self.app.dark = not self.app.dark
        self.update_log(f"[bold]Dark side: [italic]{self.app.dark}")

    def action_custom_screenshot(self, screen_dir: str = '/tmp') -> None:
        """Action that fires when the user presses 's' for a screenshot"""
        # construct the screenshot elements: name (w/ ISO timestamp) + path
        screen_name = ('amdgpu_stats_' +
                       datetime.now().isoformat().replace(":", "_") +
                       '.svg')
        # take the screenshot, recording the path for logging/notification
        outpath = self.save_screenshot(path=screen_dir, filename=screen_name)
        # construct the log/notification message, then show it
        message = f"[bold]Screenshot saved to [green]'{outpath}'"
        self.screen.mount(Notification(message))
        self.update_log(message)

    def update_log(self, message: str) -> None:
        """Update the TextLog widget with a new message."""
        self.stats_widget.text_log.write(message)

    def action_custom_tab(self) -> None:
        """Toggle between the 'Stats' and 'Logs' tabs"""
        if self.stats_widget.tabbed_container.active == "tab_stats":
            new_tab = 'tab_logs'
        else:
            new_tab = 'tab_stats'
        self.stats_widget.tabbed_container.active = new_tab
        # craft a 'tab activated' (changed) event
        # used to set the subtitle via event handling
        event = TabbedContent.TabActivated(tabbed_content=self.stats_widget.tabbed_container,
                                           tab=new_tab)
        self.on_tabbed_content_tab_activated(event)

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated):
        """Listens to 'TabActivated' event, sets subtitle"""
        # if self.tabbed_container.active == "tab_logs":
        active_title = event.tabbed_content.active.title().replace('Tab_', '')
        if event.tabbed_content.active == "tab_logs":
            self.sub_title = active_title  # pylint: disable=attribute-defined-outside-init
        elif event.tabbed_content.active == "tab_stats":
            self.sub_title = f'{active_title}: {list(AMDGPU_CARDS)}'  # pylint: disable=attribute-defined-outside-init
