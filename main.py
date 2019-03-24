from enum import Enum

import pyglet
from pyglet import gl
from pyglet.window import key
from pyglet.event import EVENT_UNHANDLED, EVENT_HANDLED
import pyglet.sprite
import pyglet.resource
import pymunk
from pymunk.vec2d import Vec2d


WIDTH = 1600   # Width in hidpi pixels
HEIGHT = 1200  # Height in hidpi pixels

PIXEL_SCALE = 1.0  # Scale down for non-hidpi screens


pyglet.resource.path = [
    'assets/',
]
pyglet.resource.reindex()


space = pymunk.Space()
space.gravity = (0, -60)

window = pyglet.window.Window(round(WIDTH * PIXEL_SCALE), round(HEIGHT * PIXEL_SCALE))


img = pyglet.resource.image('sprites/jumper.png')
img.anchor_x = img.width // 2
img.anchor_y = img.height // 2
pc = pyglet.sprite.Sprite(img)
pc.position = 400, 300


SPACE_SCALE = 1 / 30


def create_walls(space):
    walls = [
        ((-5, -5), (WIDTH + 5, -5)),
        ((-5, -5), (-5, HEIGHT + 5)),
        ((-5, HEIGHT + 5), (WIDTH + 5, HEIGHT + 5)),
        ((WIDTH + 5, -5), (WIDTH + 5, HEIGHT + 5)),
    ]
    for a, b in walls:
        a = Vec2d(*a) * SPACE_SCALE
        b = Vec2d(*b) * SPACE_SCALE
        shape = pymunk.Segment(space.static_body, a, b, 10 * SPACE_SCALE)
        shape.friction = 1
        shape.elasticity = 0.6
        space.add(shape)



create_walls(space)


body = pymunk.Body(5, pymunk.inf)
body.position = Vec2d(400, 300) * SPACE_SCALE
shape = pymunk.Poly.create_box(
    body,
    size=Vec2d(pc.width, pc.height) * SPACE_SCALE
)
shape.friction = 0.4
shape.elasticity = 0.6
space.add(body, shape)


@window.event
def on_draw():
    window.clear()
    gl.glLoadIdentity()
    gl.glScalef(PIXEL_SCALE, PIXEL_SCALE, 1)

    pc.position = body.position / SPACE_SCALE
    pc.draw()


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


keys_down = key.KeyStateHandler()
window.push_handlers(keys_down)


JUMP_IMPULSE = 200


def jump(direction):
    body.apply_impulse_at_local_point(direction.value * JUMP_IMPULSE)


@window.event
def on_key_press(symbol, modifiers):
    if symbol in INPUT_TO_JUMP:
        jump(INPUT_TO_JUMP[symbol])
    elif symbol in (key.UP, key.DOWN):
        mod = None
        if keys_down[key.LEFT]:
            mod = key.LEFT
        elif keys_down[key.RIGHT]:
            mod = key.RIGHT
        k = (mod, symbol)
        if k in INPUT_TO_JUMP:
            jump(INPUT_TO_JUMP[k])

    keys_down.on_key_press(symbol, modifiers)


def update_physics(dt):
    for _ in range(3):
        space.step(1 / 180)

pyglet.clock.schedule_interval(update_physics, 1 / 60)
pyglet.app.run()

