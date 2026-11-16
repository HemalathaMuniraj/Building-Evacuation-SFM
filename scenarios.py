"""Evacuation scenarios.  Every scenario is a full, self-describing configuration."""
from dataclasses import dataclass
from typing import Tuple
from geometry import Exit, Pillar

ROOM_W, ROOM_H = 14.0, 9.0   # metres


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    total_people: int
    exits: Tuple[Exit, ...]
    pillars: Tuple[Pillar, ...] = ()
    room: Tuple[float, float] = (ROOM_W, ROOM_H)
    exit_choice: str = "familiar"     # 'familiar' (everybody heads for exit #familiar_exit) | 'nearest'
    familiar_exit: int = 0
    speed_factor: float = 1.0         # >1 models panic (higher desired speed)
    reaction_max: float = 2.0         # pre-movement delay is uniform in [0, reaction_max] s
    slow_fraction: float = 0.05       # share of slow / mobility-impaired occupants

    @property
    def exit_available(self) -> bool:
        """Backwards-compatible flag: is at least one exit open at t = 0?"""
        return any(e.block_time != 0.0 for e in self.exits)


MAIN = Exit("right", center=4.5, width=2.0, name="Main exit")

_LIST = [
    Scenario(
        "Normal Evacuation", "One 2 m exit is available. 40 people evacuate.",
        total_people=40, exits=(MAIN,)),
    Scenario(
        "Blocked Exit",
        "Main exit is blocked from the start. People discover it at the door and re-route to the 1.2 m emergency exit.",
        total_people=40,
        exits=(Exit("right", 4.5, 2.0, block_time=0.0, name="Main exit"),
               Exit("top", 3.0, 1.2, name="Emergency exit"))),
    Scenario(
        "Late Blockage",
        "Main exit gets blocked 12 s into the evacuation (debris / fire). People already inside must re-route.",
        total_people=60,
        exits=(Exit("right", 4.5, 2.0, block_time=12.0, name="Main exit"),
               Exit("top", 3.0, 1.2, name="Emergency exit"))),
    Scenario(
        "High Density", "A higher number of pedestrians (100) uses the single exit.",
        total_people=100, exits=(MAIN,)),
    Scenario(
        "Two Exits", "Two 2 m exits on opposite walls. 100 people choose the nearest one.",
        total_people=100, exit_choice="nearest",
        exits=(Exit("right", 4.5, 2.0, name="East exit"),
               Exit("left", 4.5, 2.0, name="West exit"))),
    Scenario(
        "Pillar at Exit", "100 people, one exit, with a pillar placed in front of the door.",
        total_people=100, exits=(MAIN,), pillars=(Pillar(12.2, 4.5, 0.4),)),
    Scenario(
        "Urgent Movement",
        "100 people, no reaction delay, 60 % higher desired speed. (Plain SFM does not reproduce faster-is-slower here.)",
        total_people=100, exits=(MAIN,), speed_factor=1.6, reaction_max=0.0),
]

SCENARIOS = {s.name: s for s in _LIST}


def scenario_names():
    return [s.name for s in _LIST]


def get_scenario(name):
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}")
    return SCENARIOS[name]