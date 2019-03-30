from enum import Enum


class LevelState(Enum):
    """The state in which the game is in."""
    PLAYING = 1
    FAILED = 2
    WON = 3
    PERFECT = 4
    END = 5


class UnderwaterState(Enum):
    """Whether an actor is underwater."""

    DRY = 1
    SURFACE = 2
    UNDERWATER = 3
