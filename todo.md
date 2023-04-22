## TODO

- add unit toggle/binding; `Ghz` can be fairly vague - users may prefer `Mhz`/`Hz`
    - tldr: may be wanted for precision
    - driver provides *hertz*, with modern cards is fairly excessive
    - conversion is done using `format_frequency`
        - a wrapper of `format_size` from `humanfriendly`
        - _(currently)_ defaults to highest sensible unit, changing on scale. 
        - often flipping between `500Mhz` / `2.6Ghz` where consistency may be preferred

- restore `argparse`
    - primarily: `--card` / `-c`, to skip `amdgpu` device detection
        - will expect `cardN` or `renderANNN` from `/dev/dri/` 
        - provides the (AMD) GPU intended to be monitored
    - secondarily:
        - preferred unit for clocks
        - perhaps an update interval for the Textual stat-updating timers
