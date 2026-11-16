"""Room geometry: exits, pillars and wall construction (metres, y axis points down)."""
from dataclasses import dataclass
from typing import Optional, Sequence
import numpy as np

_NORMALS = {"right": (1.0, 0.0), "left": (-1.0, 0.0), "top": (0.0, -1.0), "bottom": (0.0, 1.0)}
_TANGENTS = {"right": (0.0, 1.0), "left": (0.0, 1.0), "top": (1.0, 0.0), "bottom": (1.0, 0.0)}


@dataclass(frozen=True)
class Exit:
    """A door in one of the four outer walls.

    side        : 'left' | 'right' | 'top' | 'bottom'
    center      : position of the door centre along that wall [m]
                  (measured from the top for left/right walls, from the left for top/bottom)
    width       : door width [m]
    block_time  : None  -> never blocked
                  0.0   -> blocked from the start
                  t > 0 -> becomes blocked at time t [s]  (e.g. fire / crowd crush / debris)
    """
    side: str
    center: float
    width: float
    block_time: Optional[float] = None
    name: str = "Exit"

    def mid(self, room_w, room_h):
        if self.side == "right":
            return np.array([room_w, self.center])
        if self.side == "left":
            return np.array([0.0, self.center])
        if self.side == "top":
            return np.array([self.center, 0.0])
        return np.array([self.center, room_h])

    @property
    def normal(self):
        return np.array(_NORMALS[self.side])

    @property
    def tangent(self):
        return np.array(_TANGENTS[self.side])

    @property
    def lo(self):
        return self.center - self.width / 2.0

    @property
    def hi(self):
        return self.center + self.width / 2.0

    def endpoints(self, room_w, room_h):
        m = self.mid(room_w, room_h)
        return m - self.tangent * self.width / 2.0, m + self.tangent * self.width / 2.0

    def is_blocked(self, t):
        return self.block_time is not None and t >= self.block_time


@dataclass(frozen=True)
class Pillar:
    """A circular obstacle (column, planter, barrier)."""
    x: float
    y: float
    radius: float


def build_walls(room_w: float, room_h: float, exits: Sequence[Exit], blocked: Sequence[bool]):
    """Return wall segments as an array of shape (M, 2, 2).

    Open exits leave a gap in the wall, blocked exits are closed with wall.
    """
    makers = {
        "left": lambda a, b: ((0.0, a), (0.0, b)),
        "right": lambda a, b: ((room_w, a), (room_w, b)),
        "top": lambda a, b: ((a, 0.0), (b, 0.0)),
        "bottom": lambda a, b: ((a, room_h), (b, room_h)),
    }
    lengths = {"left": room_h, "right": room_h, "top": room_w, "bottom": room_w}
    walls = []
    for side, make in makers.items():
        gaps = sorted((e.lo, e.hi) for e, b in zip(exits, blocked) if e.side == side and not b)
        cursor = 0.0
        for lo, hi in gaps:
            if lo > cursor:
                walls.append(make(cursor, lo))
            cursor = hi
        if cursor < lengths[side]:
            walls.append(make(cursor, lengths[side]))
    return np.array(walls, dtype=float)