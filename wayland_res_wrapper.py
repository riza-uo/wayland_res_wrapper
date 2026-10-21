#! /usr/bin/python3

import argparse
from dataclasses import dataclass, field
import json
import re
import subprocess


_MONITOR_IDS = (
    "DP-1",  # CRT
    "DP-2",  # Right Monitor
    "HDMI-A-1"  # Left Monitor
)


@dataclass
class Mode:
    name: str
    res: str = field(init=False)
    x: int = field(init=False)
    y: int = field(init=False)
    hz: int = field(init=False)

    def __post_init__(self):
        self.x, self.y, self.hz = re.split("x|@", self.name)
        self.hz = int(self.hz)
        self.res = f"{self.x}x{self.y}"


@dataclass
class Position:
    x: int
    y: int


@dataclass
class Monitor:
    """
    Helper class to clean up accessing monitor properties
    """
    id: int
    mode_id: int
    modes: dict
    position: Position
    width: int
    height: int
    priority: int

    @property
    def curr_mode(self) -> str:
        return self.modes[self.mode_id]
    
    @property
    def valid_modes(self) -> list:
        return sorted([m.name for m in self.modes.values()])

    @property
    def valid_resolutions(self) -> list:
        return sorted([m.res for m in self.modes.values()])


# TODO -- implement selectable hz
def fetch_mode(monitor: Monitor = None, res: str = None) -> Mode:
    selected_mode = None

    # Search for the mode with the correct resolution and highest hz
    for available_mode in monitor.modes.values():
        if available_mode.res != res:
            continue

        if not selected_mode:
            selected_mode = available_mode
            continue

        if available_mode.hz > selected_mode.hz:
            selected_mode = available_mode

    return selected_mode


def fetch_monitors() -> dict:
    """
    Fetch current monitor information from kscreen-doctor
    """
    monitors = {}

    ks_res = subprocess.run(["kscreen-doctor", "-j"], capture_output=True, text=True)
    ks_json = json.loads(ks_res.stdout)

    for output in ks_json["outputs"]:
        if output["name"] not in _MONITOR_IDS:
            print("ERROR - Monitor names have changed, investigate....")
            return

        monitors[output["name"]] = Monitor(
            id=output["id"],
            mode_id=output["currentModeId"],
            modes=dict((m["id"], Mode(m["name"])) for m in output["modes"]),
            position=Position(output["pos"]["x"], output["pos"]["y"]),
            width=output["size"]["width"],
            height=output["size"]["height"],
            priority=output["priority"],
        )

    return monitors


def change_monitor_res(monitor_id, mode=None) -> None:
    if not mode:
        print("ERROR - mode not provided")
        return
    subprocess.run(["kscreen-doctor", f"output.{monitor_id}.mode.{mode.name}"])


def change_monitor_pos(monitor_id, pos=None) -> None:
    if not pos:
        print("ERROR - position not provided")
        return
    subprocess.run(["kscreen-doctor", f"output.{monitor_id}.position.{pos.x},{pos.y}"])


# TODO -- Add functionality to allow passing in an alternative primary display
#      -- Primary display is reset after the game process is complete.
def set_monitor_priority(monitor_id, priority) -> None:
    if not priority:
        print("ERROR - priority not provided")
        return
    subprocess.run(["kscreen-doctor", f"output.{monitor_id}.priority.{priority}"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mode", help="Target video mode (resolution)")
    parser.add_argument("-p", "--primary", help="Target primary monitor")
    parser.add_argument("game_commands", help="automatically passed by calling program", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args:
        print("ERROR - Resolution wrapper must be supplied with a target resolution")
        return

    monitors = fetch_monitors()

    if not monitors:
        return

    target_primary = args.primary or "DP-1"

    if target_primary not in _MONITOR_IDS:
        print(f"ERROR - Target primary monitor does not exist. Available options are:")
        for monitor_name in _MONITOR_IDS:
            print(monitor_name)
        return

    # TODO -- when primary is not passed, ignore this
    set_monitor_priority(target_primary, 1)

    # Check that the target res is in the available modes for the primary monitor
    if args.mode:
        if args.mode not in monitors[target_primary].valid_resolutions:
            print(f"ERROR - Target resolution ({args.mode}) not found. Try one of the following:")
            for vm in monitors[target_primary].valid_resolutions:
                print(vm)
            return

        # Fetches the highest hz mode for a given monitor
        target_mode = fetch_mode(monitors[target_primary], args.mode)

        if not target_mode:
            print(f"ERROR - Unable to get a valid mode for target resolution: {args.mode}... Aborting")
            return

        # Set primary monitor to desired game resolution
        change_monitor_res(
            monitor_id=monitors[target_primary].id, 
            mode=target_mode
        )

        # Set right-most monitor position to ensure no gaps
        # TODO -- make this smarter, get the location dynamically using monitor pos
        change_monitor_pos(
            monitor_id=monitors["DP-2"].id,
            pos=Position(
                # Offset right-most monitor by the new width of the Left-most and center monitors
                x=int(monitors["HDMI-A-1"].width) + int(target_mode.x),
                y=0
            )
        )

    # Run game
    subprocess.run(args.game_commands)

    # Reset original state
    for m in monitors.values():
        change_monitor_res(monitor_id=m.id, mode=m.curr_mode)
        change_monitor_pos(monitor_id=m.id, pos=m.position)
        set_monitor_priority(monitor_id=m.id, priority=m.priority)


if __name__ == "__main__":
    main()
