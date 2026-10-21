# wayland_res_wrapper

A small launch wrapper for KDE Plasma on Wayland that switches a monitor to a game's **native resolution** before the game starts, then restores everything when it exits.

## Why

CRT monitors look their best when the display runs at the same resolution as the content. A classic game designed for 640x480 should drive the CRT at 640x480, not send a 640x480 image upscaled to the desktop resolution.

Proton doesn't do this. When a game requests a resolution change, Proton keeps the display at its current mode and scales the game's output up to fit. That's the right behaviour for flat panels, but on a CRT it gives up much of what makes the display worthwhile: native scanlines, sharpness, and the original resolution's timing.

This wrapper sets the real display mode with `kscreen-doctor` first, so the game launches onto a monitor that's already at the target resolution and Proton has nothing to scale.

## What it does

1. Reads the current monitor setup with `kscreen-doctor -j`.
2. Switches the target monitor (the CRT by default) to the requested resolution, using the highest refresh rate available for that resolution.
3. Adjusts the monitor layout to prevent gaps.
4. Runs the game.
5. When the game exits, restores every monitor's original mode and position.

## Requirements

- KDE Plasma on Wayland (tested on Kubuntu 26.04)
- `kscreen-doctor` (ships with Plasma)
- Python 3.7+

## Setup

Make the script executable:

```bash
chmod +x wayland_res_wrapper.py
```

Then set your output names. Find them with:

```bash
kscreen-doctor -o
```

and edit `_MONITOR_IDS` at the top of the script to match:

```bash
vim wayland_res_wrapper.py
```

The layout is currently hardcoded for a three-monitor setup with the CRT in the centre:

| Output     | Role                        |
|------------|-----------------------------|
| `HDMI-A-1` | Left monitor                |
| `DP-1`     | CRT, centre (default target)|
| `DP-2`     | Right monitor               |

If the outputs reported by `kscreen-doctor` don't match `_MONITOR_IDS`, the wrapper aborts and the game is not launched.

## Usage

### Steam

Open the game's **Properties → Launch Options** and add:

```
/path/to/wayland_res_wrapper.py -m 640x480 %command%
```

### Heroic Games Launcher

Open the game's **Settings → Advanced** and add a wrapper under **Wrappers**:

| Field     | Value                            |
|-----------|----------------------------------|
| Wrapper   | `/path/to/wayland_res_wrapper.py` |
| Arguments | `-m 640x480`                     |

Heroic appends the game command after the wrapper and its arguments.

### Options

| Flag              | Description                                                 |
|-------------------|-------------------------------------------------------------|
| `-m`, `--mode`    | Target resolution, e.g. `640x480`. Omit to leave mode as-is. |
| `-p`, `--primary` | Output to switch and make primary. Defaults to `DP-1`.      |

If you pass a resolution the monitor doesn't support, the wrapper prints the list of valid resolutions and exits without launching the game.

### Troubleshooting

If a game doesn't launch, check the logs for the wrapper's error messages:

- **Steam:** logs are written to `~/.local/share/Steam/logs/`.
- **Heroic:** open **Settings → Logs** in the sidebar and select the game.