from enum import Enum

import pyglet
from pyglet import gl
from pyglet.window import key
from pyglet.event import EVENT_UNHANDLED, EVENT_HANDLED
import pyglet.sprite
import pyglet.resource
import pymunk
from pymunk.vec2d import Vec2d


PIXEL_SCALE = 0.5


pyglet.resource.path = [
    'assets/',
]
pyglet.resource.reindex()


window = pyglet.window.Window(round(1600 * PIXEL_SCALE), round(1200 * PIXEL_SCALE))




pc = pyglet.sprite.Sprite(
    pyglet.resource.image('sprites/jumper.png')
)
pc.position = 400, 300



@window.event
def on_draw():
    window.clear()
    gl.glLoadIdentity()
    gl.glScalef(PIXEL_SCALE, PIXEL_SCALE, 1)
    pc.draw()


rt3_2 = 3 ** 0.5 / 2

class Direction(Enum):
    """The six cardinal directions for the jumps."""

    L = Vec2d(-1, 0)
    R = Vec2d(1, 0)
    UL = Vec2d(-0.5, rt3_2)
    UR = Vec2d(0.5, rt3_2)
    DL = Vec2d(-0.5, -rt3_2)
    DR = Vec2d(0.5, -rt3_2)


INPUT_TO_JUMP = {
    key.Q: Direction.UL,
    key.A: Direction.L,
    key.Z: Direction.DL,
    key.E: Direction.UR,
    key.D: Direction.R,
    key.C: Direction.DR,

    # Cursors are L/R + mod
    (key.LEFT, key.UP): Direction.UL,
    (key.LEFT, None): Direction.L,
    (key.LEFT, key.DOWN): Direction.DL,
    (key.RIGHT, key.UP): Direction.UR,
    (key.RIGHT, None): Direction.R,
    (key.RIGHT, key.DOWN): Direction.DR,
}


keys_down = key.KeyStateHandler()
window.push_handlers(keys_down)


def jump(direction):
    pc.position += direction.value * 50


@window.event
def on_key_press(symbol, modifiers):
    if symbol in INPUT_TO_JUMP:
        jump(INPUT_TO_JUMP[symbol])
    elif symbol in (key.LEFT, key.RIGHT):
        mod = None
        if keys_down[key.UP]:
            mod = key.UP
        elif keys_down[key.DOWN]:
            mod = key.DOWN
        k = (symbol, mod)
        if k in INPUT_TO_JUMP:
            jump(INPUT_TO_JUMP[k])

    keys_down.on_key_press(symbol, modifiers)

pyglet.app.run()

