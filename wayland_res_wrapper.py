#! /usr/bin/python3

from dataclasses import dataclass, field
import json
import re
import subprocess
import sys


_PORTRAIT_ROTATION = (2, 8)


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
    curr_mode_id: int
    modes: dict
    position: Position
    portrait: bool

    @property
    def curr_mode(self) -> str:
        return self.modes[self.curr_mode_id]
    
    @property
    def valid_modes(self) -> list:
        return [m.name for m in self.modes.values()]

    @property
    def width(self) -> int:
        return self.curr_mode.y if self.portrait else self.curr_mode.x

    @property
    def height(self) -> int:
        return self.curr_mode.x if self.portrait else self.curr_mode.y


def fetch_monitors() -> dict:
    """
    Fetch current monitor information from kscreen-doctor
    """
    monitors = {}

    ks_res = subprocess.run(["kscreen-doctor", "-j"], capture_output=True, text=True)
    ks_json = json.loads(ks_res.stdout)

    for o in ks_json["outputs"]:
        monitors[o["id"]] = Monitor(
            o["id"],
            o["currentModeId"],
            dict((m["id"], Mode(m["name"])) for m in o["modes"]),
            Position(o["pos"]["x"], o["pos"]["y"]),
            o["rotation"] in _PORTRAIT_ROTATION
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
    if target_res.name not in monitors[1].valid_modes:
        print(f"ERROR - Target resolution ({target_res.name}) not found. Try one of the following:")
        for vm in monitors[1].valid_modes:
            print(vm)
        return

    # Set primary monitor to desired game resolution
    change_monitor_res(monitor_id=1, mode=target_res)

    # Set right-most monitor position to ensure no gaps
    change_monitor_pos(
        monitor_id=2,
        pos=Position(
            # Offset right-most monitor by the new width of the Left-most and center monitors
            x=int(target_res.x) + int(monitors[3].width),
            y=0
        )
    )

    # Run game
    subprocess.run(game_commands)

    # Reset original state
    for id, m in monitors.items():
        change_monitor_res(monitor_id=id, mode=m.curr_mode)
        change_monitor_pos(monitor_id=id, pos=m.position)


if __name__ == "__main__":
    main()
