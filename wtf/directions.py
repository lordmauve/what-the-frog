from enum import Enum

from pymunk import Vec2d


rt3_2 = 3 ** 0.5 / 2


class DirectionLR(Enum):
    """The six cardinal directions for the jumps."""

    L = Vec2d(-1, 0)
    R = Vec2d(1, 0)
    UL = Vec2d(-0.5, rt3_2)
    UR = Vec2d(0.5, rt3_2)
    DL = Vec2d(-0.5, -rt3_2)
    DR = Vec2d(0.5, -rt3_2)


class Direction(Enum):
    """The six cardinal directions for the jumps."""

    UL = Vec2d(-rt3_2, 0.5)
    U = Vec2d(0, 1)
    UR = Vec2d(rt3_2, 0.5)
    DL = Vec2d(-rt3_2, -0.5)
    D = Vec2d(0, -1)
    DR = Vec2d(rt3_2, -0.5)

