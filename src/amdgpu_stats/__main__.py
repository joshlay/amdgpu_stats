"""TUI for amdgpu_stats

This file aims to ensure the TUI only starts in interactive shells

import/use 'amdgpu_stats.utils' to access functions for metrics"""

from . import textual_run

if __name__ == "__main__":
    textual_run()
else:
    pass
