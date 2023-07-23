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
from yaml import dump

from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import (
        DataTable,
        Footer,
        Header,
        Label,
        ProgressBar,
        Static,
        TabbedContent,
        TabPane,
        TextLog,
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

class GPUStatsWidget(Static):
    """The main stats widget."""

    def get_column_data_mapping(self, card: Optional[str] = None) -> dict:
        '''Returns a dictionary of stats

        Columns are derived from keys, and values provide measurements
        *Measurements require `card`*'''
        # handle varying stats (among cards) independently
        #
        # first, a subset of the power stats - gather them all
        # ... then map to a smaller dict that's used to update the table
        _all_pwr = get_power_stats(card=card)
        power_stats = {
                "usage": _all_pwr["average"],
                "lim": _all_pwr["limit"],
                "def": _all_pwr["default"],
                "cap": _all_pwr["capability"],
                }

        temp_stats = {
                "edge": get_temp_stat(name='edge', card=card),
                "junction": get_temp_stat(name='junction', card=card),
                "memory": get_temp_stat(name='mem', card=card)
                }

        # 'humanize' values, add units
        for power_stat, val in power_stats.items():
            if val is None:
                power_stats[power_stat] = 'Unknown'
            else:
                power_stats[power_stat] = str(val) + 'W'
        for temp_stat, val in temp_stats.items():
            if val is None:
                temp_stats[temp_stat] = 'N/A'
            else:
                temp_stats[temp_stat] = str(val) + 'C'

        if card is None:
            return {
                "Card": "",
                "Core clock": "",
                "Memory clock": "",
                "Utilization": "",
                "Voltage": "",
                "Power": "",
                "Limit": "",
                "Default": "",
                "Capability": "",
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
            "Power": power_stats['usage'],
            "Limit": power_stats['lim'],
            "Default": power_stats['def'],
            "Capability": power_stats['cap'],
            "Fan RPM": f'{get_fan_rpm(card=card)}',
            "Edge temp": temp_stats['edge'],
            "Junction temp": temp_stats['junction'],
            "Memory temp": temp_stats['memory']
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
        self.update_log("[bold green]App started, logging begin!\n")
        # construct the table columns
        columns = list(self.get_column_data_mapping(None).keys())
        for column in columns:
            if column in ['Limit', 'Default', 'Capability']:
                self.stats_table.add_column(label='[italic]' + column,
                                            key=column)
            else:
                self.stats_table.add_column(label=column, key=column)
        #    self.update_log(f'  - "{column}"')
        self.update_log('[bold]Stat columns:')
        self.update_log(dump(data=columns, default_flow_style=False, sort_keys=True))
        # do a one-off stat collection, populate table before the interval
        self.get_stats()
        # stand up the stat-collecting interval, twice per second
        self.timer_stats = self.set_interval(1.0, self.get_stats)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with self.tabbed_container:
            with TabPane("Stats", id="tab_stats"):
                yield self.stats_table
            with TabPane("Graphs", id="tab_graphs", classes="tab_graphs"):
                for card in AMDGPU_CARDS:
                    yield Vertical(
                            Label(f'[bold]{card}'),
                            Label('Core:'),
                            ProgressBar(total=100.0,
                                        show_eta=False,
                                        id='bar_' + card + '_util'),
                            )
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
            # Update usage bars
            if self.data['Utilization'] is not None:
                self.query_one(f'#bar_{card}_util').update(total=100, progress=float(self.data['Utilization'].replace('%', '')))
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
                self.update_log(f"Added row for '{card}', stats dir: '{hwmon_dir}'")
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
    # set a default subtitle, will change with the active tab
    SUB_TITLE = f'cards: {list(AMDGPU_CARDS)}'

    # setup keybinds
    BINDINGS = [
        Binding("c", "custom_dark", "Colors"),
        Binding("t", "custom_tab", "Tab switch"),
        Binding("s", "custom_screenshot", "Screenshot"),
        Binding("up,k", "custom_logscroll('up')", "Scroll Logs", ),
        Binding("down,j", "custom_logscroll('down')", "Scroll Logs"),
        Binding("pageup", "custom_logscroll('pageup')", "", show=False),
        Binding("pagedown", "custom_logscroll('pagedown')", "", show=False),
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
        # inline conditional due to how Textual doesn't pretty notifs. for us like TextLog
        message = f"[bold]Dark side: [italic][{'green' if self.app.dark else 'red'}]{self.app.dark}"
        self.notify(message)
        self.update_log(message)

    async def action_custom_logscroll(self, direction: str) -> None:
        """Action that handles scrolling of the logging widget

        'j', 'k', 'Up'/'Down' arrows handle line-by-line
        Page Up/Down do... pages"""
        if direction == "pageup":
            self.stats_widget.text_log.scroll_page_up(animate=True, speed=None, duration=0.175)
        elif direction == "up":
            self.stats_widget.text_log.scroll_up(animate=False)
        elif direction == "pagedown":
            self.stats_widget.text_log.scroll_page_down(animate=True, speed=None, duration=0.175)
        elif direction == "down":
            self.stats_widget.text_log.scroll_down(animate=False)

    async def action_custom_screenshot(self, screen_dir: str = '/tmp') -> None:
        """Action that fires when the user presses 's' for a screenshot"""
        # construct the screenshot elements: name (w/ ISO timestamp) + path
        screen_name = ('amdgpu_stats_' +
                       datetime.now().isoformat().replace(":", "_") +
                       '.svg')
        # take the screenshot, recording the path for logging/notification
        outpath = self.save_screenshot(path=screen_dir, filename=screen_name)
        # construct the log/notification message, then show it
        message = f"[bold]Path: [/]'[green]{outpath}[/]'"
        self.notify(message, title='Screenshot captured', timeout=3.0)
        self.update_log(message)

    def update_log(self, message: str) -> None:
        """Update the TextLog widget with a new message."""
        self.stats_widget.text_log.write(message)

    def action_custom_tab(self) -> None:
        """Toggle between the 'Stats' and 'Logs' tabs"""
        # walk/cycle the tabs
        if self.stats_widget.tabbed_container.active == "tab_stats":
            new_tab = 'tab_graphs'
        elif self.stats_widget.tabbed_container.active == "tab_graphs":
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
        active_tab = event.tabbed_content.active.replace('tab_', '')
        if active_tab == "logs":
            self.sub_title = active_tab  # pylint: disable=attribute-defined-outside-init
        elif active_tab == "stats":
            self.sub_title = f'cards: {list(AMDGPU_CARDS)}'  # pylint: disable=attribute-defined-outside-init
