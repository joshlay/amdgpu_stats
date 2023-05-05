"""__init__.py for amdgpu-stats"""

import sys
from .tui import app
from .utils import (
        AMDGPU_CARDS,
)


def check_for_cards() -> bool:
    """Used by '__main__' and 'textual_run', they should exit w/ a message if no cards

    Returns:
        bool: If any AMD cards found or not"""
    if len(AMDGPU_CARDS) > 0:
        return True
    return False


def textual_run() -> None:
    """runs the AMD GPU Stats TUI; called only when in an interactive shell"""
    if check_for_cards():
        amdgpu_stats_app = app(watch_css=True)
        amdgpu_stats_app.run()
    else:
        sys.exit('Could not find an AMD GPU, exiting.')
