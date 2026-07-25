#! /usr/bin/python3

from dataclasses import dataclass, field
import json
import re
import subprocess
import sys


_MONITOR_NAMES = (
    "DP-1",
    "DP-2",
    "HDMI-A-1"
)

@dataclass
class Mode:
    name: str
    x: int = field(init=False)
    y: int = field(init=False)
    hz: int = field(init=False)

    def __post_init__(self):
        self.x, self.y, self.hz = re.split("x|@", self.name)


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

    @property
    def curr_mode(self) -> str:
        return self.modes[self.mode_id]
    
    @property
    def valid_modes(self) -> list:
        return [m.name for m in self.modes.values()]


def fetch_monitors() -> dict:
    """
    Fetch current monitor information from kscreen-doctor
    """
    monitors = {}

    ks_res = subprocess.run(["kscreen-doctor", "-j"], capture_output=True, text=True)
    ks_json = json.loads(ks_res.stdout)

    for o in ks_json["outputs"]:
        if o["name"] not in _MONITOR_NAMES:
            print("ERROR - Monitor names have changed, investigate....")
            return

        monitors[o["name"]] = Monitor(
            id=o["id"],
            mode_id=o["currentModeId"],
            modes=dict((m["id"], Mode(m["name"])) for m in o["modes"]),
            position=Position(o["pos"]["x"], o["pos"]["y"]),
            width=o["size"]["width"],
            height=o["size"]["height"],
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


def main():
    if not sys.argv:
        print("ERROR - Resolution wrapper must be supplied with a target resolution")
        return

    monitors = fetch_monitors()

    if not monitors:
        return

    target_res = Mode(sys.argv[1])
    game_commands = sys.argv[2:]

    # Check that the target res is in the available modes for the primary monitor
    if target_res.name not in monitors["DP-1"].valid_modes:
        print(f"ERROR - Target resolution ({target_res.name}) not found. Try one of the following:")
        for vm in monitors["DP-1"].valid_modes:
            print(vm)
        return

    # Set primary monitor to desired game resolution
    change_monitor_res(monitor_id=monitors["DP-1"].id, mode=target_res)

    # Set right-most monitor position to ensure no gaps
    change_monitor_pos(
        monitor_id=monitors["HDMI-A-1"].id,
        pos=Position(
            # Offset right-most monitor by the new width of the Left-most and center monitors
            x=int(monitors["DP-2"].width) + int(target_res.x),
            y=0
        )
    )

    # Run game
    subprocess.run(game_commands)

    # Reset original state
    for m in monitors.values():
        change_monitor_res(monitor_id=m.id, mode=m.curr_mode)
        change_monitor_pos(monitor_id=m.id, pos=m.position)


if __name__ == "__main__":
    main()
