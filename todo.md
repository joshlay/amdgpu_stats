## TODO

- add unit toggle/binding; `Ghz` can be fairly vague - users may prefer `Mhz`/`Hz`
    - tldr: may be wanted for precision
    - driver provides *hertz*, with modern cards is fairly excessive
    - conversion is done using `format_frequency`; a wrapper of `format_size` from `humanfriendly`

- restore `argparse`
    - primarily: `--card` / `-c`, to skip `amdgpu` device detection
    - perhaps an update interval for the Textual stat-updating timers
