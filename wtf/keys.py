from typing import Callable
import pyglet.window
from pyglet.window import key
from pyglet.event import EVENT_UNHANDLED, EVENT_HANDLED

from . import main
from .state import LevelState
from .screenshot import take_screenshot
from .directions import Direction, DirectionLR


# Input scheme for LR directions
INPUT_TO_JUMP_LR = {
    key.Q: DirectionLR.UL,
    key.A: DirectionLR.L,
    key.Z: DirectionLR.DL,
    key.E: DirectionLR.UR,
    key.D: DirectionLR.R,
    key.C: DirectionLR.DR,

    # Cursors are L/R + mod
    (key.LEFT, key.UP): DirectionLR.UL,
    (key.LEFT, None): DirectionLR.L,
    (key.LEFT, key.DOWN): DirectionLR.DL,
    (key.RIGHT, key.UP): DirectionLR.UR,
    (key.RIGHT, None): DirectionLR.R,
    (key.RIGHT, key.DOWN): DirectionLR.DR,
}


# Input scheme for UD directions
INPUT_TO_JUMP = {
    key.Q: Direction.UL,
    key.W: Direction.U,
    key.E: Direction.UR,
    key.A: Direction.DL,
    key.S: Direction.D,
    key.D: Direction.DR,

    # Cursors are mod + U/D
    (key.LEFT, key.UP): Direction.UL,
    (None, key.UP): Direction.U,
    (key.RIGHT, key.UP): Direction.UR,
    (key.LEFT, key.DOWN): Direction.DL,
    (None, key.DOWN): Direction.D,
    (key.RIGHT, key.DOWN): Direction.DR,
}

JUMP_KEYS = {*INPUT_TO_JUMP, key.UP, key.DOWN, key.LEFT, key.RIGHT}


class KeyInputHandler(key.KeyStateHandler):
    def __init__(
            self,
            jump: Callable[[Direction], None],
            window: pyglet.window.Window):
        self.jump = jump
        self.window = window

    def handle_jump(self, symbol):
        """Called when a jump is triggered."""
        if symbol in INPUT_TO_JUMP:
            self.jump(INPUT_TO_JUMP[symbol])
        elif symbol in (key.UP, key.DOWN):
            mod = None
            if self[key.LEFT]:
                mod = key.LEFT
            elif self[key.RIGHT]:
                mod = key.RIGHT
            k = (mod, symbol)
            if k in INPUT_TO_JUMP:
                self.jump(INPUT_TO_JUMP[k])

    def default_key_press(self, symbol, modifiers):
        if symbol == key.F12:
            take_screenshot(self.window)

        return super().on_key_press(symbol, modifiers)

    def on_key_press(self, symbol, modifiers):
        self.handle_jump(symbol)
        return self.default_key_press(symbol, modifiers)


class SlowMoKeyInputHandler(KeyInputHandler):
    """A key handler that drops into slow-mo when you hold a key."""

    def on_key_release(self, symbol, modifiers):
        self.handle_jump(symbol)
        ret = super().on_key_release(symbol, modifiers)
        main.slowmo = any(self[k] for k in JUMP_KEYS)
        return ret

    def on_key_press(self, symbol, modifiers):
        if symbol in JUMP_KEYS:
            main.slowmo = True

        return self.default_key_press(symbol, modifiers)


class RestartKeyHandler:
    def __init__(self, level):
        self.last_key = None
        self.level = level

    def on_key_press(self, symbol, modifiers):
        if self.level.state is not LevelState.PLAYING:
            if symbol == key.ESCAPE and \
                    self.level.state is not LevelState.PERFECT:
                self.level.reload()
                return EVENT_HANDLED
            elif self.level.won:
                self.level.next_level()
                return EVENT_HANDLED

        if symbol == key.ESCAPE:
            if self.last_key == key.ESCAPE:
                main.exit()
                return EVENT_HANDLED
            self.level.reload()
            self.last_key = symbol
            return EVENT_HANDLED

        self.last_key = symbol
        return EVENT_UNHANDLED
