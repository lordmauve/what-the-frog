from enum import Enum
from math import sin

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


GRAVITY = Vec2d(0, -50)
BUOYANCY = Vec2d(0, 500)
WATER_DRAG = 20

space = pymunk.Space()
space.gravity = GRAVITY

window = pyglet.window.Window(round(WIDTH * PIXEL_SCALE), round(HEIGHT * PIXEL_SCALE))


sprites = pyglet.graphics.Batch()

platform = pyglet.resource.image('sprites/platform.png')
platforms = []


# Collision types for callbacks
COLLISION_TYPE_WATER = 1
COLLISION_TYPE_COLLECTIBLE = 2
COLLISION_TYPE_FROG = 3


def phys_to_screen(v, v2=None):
    if v2:
        return Vec2d(v, v2) / SPACE_SCALE
    return Vec2d(*v) / SPACE_SCALE


def screen_to_phys(v, v2=None):
    if v2:
        return Vec2d(v, v2) * SPACE_SCALE
    return Vec2d(*v) * SPACE_SCALE

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
    shape.friction = 0.6
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
        shape.friction = 0
        shape.elasticity = 0.6
        space.add(shape)


class Tongue:
    TEX = pyglet.resource.texture('sprites/tongue.png')
    ordering = pyglet.graphics.OrderedGroup(1)
    group = pyglet.sprite.SpriteGroup(
        TEX,
        gl.GL_SRC_ALPHA,
        gl.GL_ONE_MINUS_SRC_ALPHA,
        parent=ordering
    )

    def __init__(self, mouth_pos, fly_pos):
        self.mouth_pos = mouth_pos
        self.fly_pos = fly_pos
        self.length = 0

        self.dl = sprites.add(
            4,
            gl.GL_QUADS,
            self.group,
            'v2f/stream',
            't3f/static',
        )
        self.dl.tex_coords = self.TEX.tex_coords
        self.recalc_verts()

    def recalc_verts(self):
        """Recalculate the vertices from current fly and mouth pos."""
        tongue_w = self.TEX.height

        along = self.fly_pos - self.mouth_pos
        across = along.normalized().rotated(90) * tongue_w * 0.5

        along *= self.length

        self.dl.vertices = [c for v in [
            self.mouth_pos - across,
            self.mouth_pos - across + along,
            self.mouth_pos + across + along,
            self.mouth_pos + across,
        ] for c in v]

    def delete(self):
        self.dl.delete()


class Frog:
    SPRITE = pyglet.resource.image('sprites/jumper.png')
    #img.anchor_x = img.width // 2
    SPRITE.anchor_y = 5

    def __init__(self, x, y):
        self.sprite = pyglet.sprite.Sprite(self.SPRITE, batch=sprites)
        self.sprite.position = phys_to_screen(x, y)
        self.body = pymunk.Body(5, pymunk.inf)
        self.body.position = (x, y)
        self.shape = box(
            self.body,
            0, 0,
            w=self.SPRITE.width * SPACE_SCALE,
            h=(self.SPRITE.height - 5) * SPACE_SCALE,
        )
        self.shape.obj = self
        self.shape.collision_type = COLLISION_TYPE_FROG
        self.shape.friction = 0.8
        self.shape.elasticity = 0.2

        space.add(self.body, self.shape)
        pyglet.clock.schedule_interval(self.update, 1 / 60)

        self.tongue = None

    def lick(self, pos):
        if self.tongue:
            self.tongue.fly_pos = pos
            self.tongue.length = 0
            self.tongue.t = 0
            pyglet.clock.unschedule(self._stop_lick)
        else:
            self.tongue = Tongue(self.mouth_pos, pos)
            self.tongue.t = 0

    @property
    def mouth_pos(self):
        return Vec2d(*self.sprite.position) + Vec2d(32, 20)

    def update(self, dt):
        self.sprite.position = self.body.position / SPACE_SCALE

        # Update the tongue
        if self.tongue:
            self.tongue.t += dt
            t = self.tongue.t
            if t >= 0.1:
                self.tongue.delete()
                self.tongue = None
            else:
                self.tongue.length = 400 * t * (0.1 - t)
                self.tongue.mouth_pos = self.mouth_pos
                self.tongue.recalc_verts()


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

    CONV = np.array([0.3, -0.8, 0.3])

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
        self.velocities *= 0.8 ** dt  # damp
        self.levels += self.velocities * 10 * dt  # apply velocity
        self.levels *= 0.95 ** dt

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
        dt = space.current_time_step
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
            f = 0.8 ** dt
            inst.velocities[l:r] = (
                inst.velocities[l:r] * f +
                body.velocity.y * abs(body.velocity.y) * 0.1 * (1.0 - f)
            )

        force = (BUOYANCY * bb.area() - body.velocity * WATER_DRAG) * frac_immersed
        body.apply_force_at_local_point(
            force,
            body.center_of_gravity,
        )
        return False

    handler = space.add_wildcard_collision_handler(COLLISION_TYPE_WATER)
    handler.pre_solve = pre_solve


class Fly:
    SPRITE = pyglet.resource.image('sprites/fly.png')
    SPRITE.anchor_x = SPRITE.width // 2
    SPRITE.anchor_y = SPRITE.height // 3

    CATCH_RADIUS = 2.5

    def __init__(self, x, y):
        self.pos = Vec2d(x + 0.5, y + 0.5)
        self.t = 0
        self.sprite = pyglet.sprite.Sprite(
            self.SPRITE,
            batch=sprites,
            usage='stream'
        )

        self.shape = pymunk.Circle(space.static_body, self.CATCH_RADIUS, offset=(x, y))
        self.shape.collision_type = COLLISION_TYPE_COLLECTIBLE
        self.shape.obj = self
        space.add(self.shape)

        pyglet.clock.schedule_interval(self.update, 1 / 20)
        self.update(random.uniform(0, 5))

    def update(self, dt):
        self.t += dt
        self.sprite._scale_y *= -1
        self.sprite._rotation = 10 * sin(self.t)
        self.sprite._x, self.sprite._y= phys_to_screen(
            self.pos
            + Vec2d(0.5 * sin(2 * self.t), 0.5 * sin(3 * self.t))  # lissajous wander
        )
        self.sprite._update_position()

    def collect(self):
        self.sprite.delete()
        space.remove(self.shape)
        pyglet.clock.unschedule(self.update)


def on_collect(arbiter, space, data):
    """Called when a collectible is hit"""
    fly, frog = arbiter.shapes
    frog.obj.lick(fly.obj.sprite.position)
    fly.obj.collect()
    space.remove(fly)
    return False


handler = space.add_collision_handler(COLLISION_TYPE_COLLECTIBLE, COLLISION_TYPE_FROG)
handler.begin = on_collect


pc = Frog(6, 7)
create_platform(-1, 7)
create_platform(5, 6)
create_platform(5, 17)
create_platform(13, 9)
create_walls(space)
w = Water(6.5)
pyglet.clock.schedule_interval(w.update, 1 / 60)

flies = [
    Fly(3, 10),
    Fly(16, 16),
]


fps_display = pyglet.clock.ClockDisplay()

@window.event
def on_draw():
    window.clear()
    gl.glLoadIdentity()
    gl.glScalef(PIXEL_SCALE, PIXEL_SCALE, 1)

    sprites.draw()
    w.draw()
    fps_display.draw()


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



IMPULSE_SCALE = 26
JUMP_IMPULSES = {
    Direction.UL: Vec2d.unit().rotated_degrees(30) * IMPULSE_SCALE,
    Direction.U: Vec2d.unit() * IMPULSE_SCALE,
    Direction.UR: Vec2d.unit().rotated_degrees(-30) * IMPULSE_SCALE,
    Direction.DL: Vec2d.unit().rotated_degrees(180 - 30) * IMPULSE_SCALE,
    Direction.D: Vec2d.unit().rotated_degrees(180) * IMPULSE_SCALE,
    Direction.DR: Vec2d.unit().rotated_degrees(180 + 30) * IMPULSE_SCALE,
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
    pc.body.velocity = JUMP_IMPULSES[direction]


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

