from __future__ import annotations

from dataclasses import dataclass
from pyglet.window import key

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


@dataclass
class KeyInputHandler(key.KeyStateHandler):
    jump: Callable[[Direction], None]
    window: pyglet.window.Window

    def on_key_press(self, symbol, modifiers):
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

        if symbol == key.F12:
            take_screenshot(self.window)

        return super().on_key_press(symbol, modifiers)
