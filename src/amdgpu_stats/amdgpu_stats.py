#!/usr/bin/python3
"""Pretty Textual-based stats for AMD GPUs

TODO: restore argparse / --card, in case detection fails.
      will require separating the hwmon finding tasks from 'find_card'

rich markup reference:
    https://rich.readthedocs.io/en/stable/markup.html
"""

if __name__ == "__main__":
    from .interface import tui
    tui()
