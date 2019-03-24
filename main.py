from enum import Enum

import pyglet
from pyglet import gl
from pyglet.window import key
from pyglet.graphics import Batch
from pyglet.event import EVENT_UNHANDLED, EVENT_HANDLED
import pyglet.sprite
import pyglet.resource
import pymunk
import random
from pymunk.vec2d import Vec2d

import numpy as np


WIDTH = 1600   # Width in hidpi pixels
HEIGHT = 1200  # Height in hidpi pixels

PIXEL_SCALE = 1.0  # Scale down for non-hidpi screens


pyglet.resource.path = [
    'assets/',
]
pyglet.resource.reindex()


# Space units are 64 screen pixels
SPACE_SCALE = 1 / 64


GRAVITY = Vec2d(0, -60)
BUOYANCY = Vec2d(0, 500)

space = pymunk.Space()
space.gravity = GRAVITY

window = pyglet.window.Window(round(WIDTH * PIXEL_SCALE), round(HEIGHT * PIXEL_SCALE))


sprites = pyglet.graphics.Batch()

platform = pyglet.resource.image('sprites/platform.png')
platforms = []


# Collision types for callbacks
COLLISION_TYPE_WATER = 1


def phys_to_screen(v, v2=None):
    if v2:
        return Vec2d(v, v2) / SPACE_SCALE
    return Vec2d(*v) / SPACE_SCALE


def create_platform(x, y):
    """Create a platform.

    Here x and y are in physics coordinates.

    """
    s = pyglet.sprite.Sprite(platform, batch=sprites)
    s.position = phys_to_screen(x, y)
    platforms.append(s)

    shape = box(
        space.static_body,
        x, y, 3,1
    )
    shape.friction = 0.4
    shape.elasticity = 0.6
    space.add(shape)


def box(body, x, y, w, h):
    """Create a pymunk box."""
    bl = Vec2d(x, y)
    w = Vec2d(w, 0)
    h = Vec2d(0, h)
    shape = pymunk.Poly(
        body,
        [
            bl,
            bl + w,
            bl + w + h,
            bl + h,
        ]
    )
    return shape



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


def create_pc(x, y):
    global pc, pc_body
    img = pyglet.resource.image('sprites/jumper.png')
    #img.anchor_x = img.width // 2
    img.anchor_y = 5
    pc = pyglet.sprite.Sprite(img, batch=sprites)
    pc.position = phys_to_screen(x, y)
    pc_body = pymunk.Body(5, pymunk.inf)
    pc_body.position = (x, y)
    shape = box(
        pc_body,
        0, 0,
        w=pc.width * SPACE_SCALE,
        h=(pc.height - 5) * SPACE_SCALE,
    )
    shape.friction = 0.4
    shape.elasticity = 0.6
    space.add(pc_body, shape)


create_pc(6, 4)
create_platform(-1, 4)
create_platform(5, 3)
create_walls(space)


class Water:
    class WaterGroup(pyglet.graphics.Group):
        def set_state(self):
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            gl.glColor4f(0.3, 0.5, 0.9, 0.3)

        def unset_state(self):
            gl.glColor4f(1, 1, 1, 1)
            gl.glDisable(gl.GL_BLEND)

    water_batch = pyglet.graphics.Batch()
    group = WaterGroup()

    CONV = np.array([0.1, 0.3, -0.8, 0.3, 0.1])

    SUBDIV = 5

    def __init__(self, surf_y, x1=0, x2=WIDTH * SPACE_SCALE, bot_y=-1000):
        self.y = surf_y
        self.x1 = x1
        self.x2 = x2

        self.shape = box(
            space.static_body,
            x=x1,
            y=bot_y,
            w=x2 - x1,
            h=surf_y - bot_y
        )
        self.shape.water = self
        self.shape.collision_type = COLLISION_TYPE_WATER
        space.add(self.shape)

        size = int(x2 - x1) * self.SUBDIV + 1
        self.xs = np.linspace(x1, x2, size)
        self.velocities = np.zeros(size)
        self.levels = np.zeros(size)
        self.bot_verts = np.ones(size) * bot_y
        self.dl = self.water_batch.add(
            size * 2,
            gl.GL_TRIANGLE_STRIP,
            self.group,
            'v2f/stream'
        )

    def update(self, dt):
        self.velocities += np.convolve(
            self.levels,
            self.CONV,
            'same',
        )
        self.velocities *= 0.5 ** dt  # damp
        self.levels += self.velocities * 10 * dt  # apply velocity
        self.levels *= 0.9 ** dt

        verts = np.dstack((
            self.xs,
            self.levels + self.y,
            self.xs,
            self.bot_verts,
        )) / SPACE_SCALE

        self.dl.vertices = np.reshape(verts, (-1, 1))

    def drip(self, _):
        self.levels[-9] = -0.5
        self.velocities[-9] = 0

    @classmethod
    def draw(cls):
        cls.water_batch.draw()

    def pre_solve(arbiter, space, data):
        water, actor = arbiter.shapes
        body = actor.body
        if not body:
            return False

        inst = water.water

        water_y = inst.y
        bb = actor.cache_bb()

        l = round(bb.left - inst.x1) * inst.SUBDIV
        r = round(bb.right - inst.x1) * inst.SUBDIV
        levels = inst.levels[l:r] + inst.y
        frac_immersed = float(np.mean(np.clip(
            (levels - bb.bottom) / (bb.top - bb.bottom),
            0, 1
        )))
        if frac_immersed < 1:
            inst.velocities[l:r] += body.velocity.y * 0.003

        force = (BUOYANCY * bb.area() - body.velocity * 10) * frac_immersed
        body.apply_force_at_local_point(
            force,
            body.center_of_gravity,
        )
        return False

    handler = space.add_wildcard_collision_handler(COLLISION_TYPE_WATER)
    handler.pre_solve = pre_solve



w = Water(3.5)


pyglet.clock.schedule_interval(w.update, 1 / 60)


@window.event
def on_draw():
    window.clear()
    gl.glLoadIdentity()
    gl.glScalef(PIXEL_SCALE, PIXEL_SCALE, 1)

    pc.position = pc_body.position / SPACE_SCALE
    sprites.draw()
    w.draw()


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



IMPULSE_SCALE = 140
JUMP_IMPULSES = {
    Direction.UL: Vec2d.unit().rotated_degrees(30) * IMPULSE_SCALE,
    Direction.U: Vec2d.unit() * IMPULSE_SCALE,
    Direction.UR: Vec2d.unit().rotated_degrees(-30) * IMPULSE_SCALE,
    Direction.DL: Vec2d.unit().rotated_degrees(180 - 45) * IMPULSE_SCALE,
    Direction.D: Vec2d.unit().rotated_degrees(180) * IMPULSE_SCALE,
    Direction.DR: Vec2d.unit().rotated_degrees(180 + 45) * IMPULSE_SCALE,
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


def jump(direction):
    pc_body.apply_impulse_at_local_point(JUMP_IMPULSES[direction])


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

