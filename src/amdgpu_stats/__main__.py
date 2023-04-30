"""TUI for amdgpu_stats

This file aims to ensure the TUI only starts in interactive shells"""
from .tui import start


def main():
    """main function, spawns the TUI for amdgpu_stats"""
    start()


if __name__ == "__main__":
    main()
