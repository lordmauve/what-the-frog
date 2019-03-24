from enum import Enum
from math import sin
import pathlib
import random
import datetime
from itertools import count

import pyglet
from pyglet import gl
from pyglet.window import key
import pyglet.sprite
import pyglet.resource
import pymunk
from pymunk.vec2d import Vec2d
import moderngl

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


mgl = moderngl.create_context()

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

    VCONV = np.array([0.05, 0.3, -0.8, 0.3, 0.05])
    LCONV = np.array([0.05, 0.9, 0.05])

    SUBDIV = 5

    def __init__(self, surf_y, x1=0, x2=WIDTH * SPACE_SCALE, bot_y=0):
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
            self.VCONV * (dt * 60),
            'same',
        )
        self.velocities *= 0.5 ** dt  # damp
        self.levels = np.convolve(
            self.levels,
            self.LCONV,
            'same'
        ) + self.velocities * 10 * dt  # apply velocity

        verts = np.dstack((
            self.xs,
            self.levels + self.y,
            self.xs,
            self.bot_verts,
        ))
        self.vertices = verts
        #self.dl.vertices = np.reshape(verts, (-1, 1))

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

        bb = actor.cache_bb()

        a = round(bb.left - inst.x1) * inst.SUBDIV
        b = round(bb.right - inst.x1) * inst.SUBDIV
        levels = inst.levels[a:b] + inst.y
        frac_immersed = float(np.mean(np.clip(
            (levels - bb.bottom) / (bb.top - bb.bottom),
            0, 1
        )))
        if frac_immersed < 1:
            f = 0.6 ** dt
            inst.velocities[a:b] = (
                inst.velocities[a:b] * f +
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
        self.sprite.position = phys_to_screen(self.pos)

        self.shape = pymunk.Circle(space.static_body, self.CATCH_RADIUS, offset=(x, y))
        self.shape.collision_type = COLLISION_TYPE_COLLECTIBLE
        self.shape.obj = self
        space.add(self.shape)
        self.update(random.uniform(0, 5))

    def update(self, dt):
        self.t += dt
        self.sprite._scale_y *= -1
        self.sprite._rotation = 10 * sin(self.t)
        self.sprite._x, self.sprite._y = phys_to_screen(
            self.pos
            + Vec2d(0.5 * sin(2 * self.t), 0.5 * sin(3 * self.t))  # lissajous wander
        )
        self.sprite._update_position()

    def collect(self):
        flies.remove(self)
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

water = [
    Water(6.5),
]

flies = [
    Fly(3, 10),
    Fly(16, 16),
]


fps_display = pyglet.clock.ClockDisplay()


size = (WIDTH, HEIGHT)
fbuf = mgl.framebuffer(
    [mgl.texture(size, components=3)],
    mgl.depth_renderbuffer(size)
)
lights = mgl.simple_framebuffer((WIDTH, HEIGHT))


lights_shader = mgl.program(
    vertex_shader='''
        #version 130

        in vec2 vert;

        varying vec2 uv;

        void main() {
            gl_Position = vec4(vert, 0.0, 1.0);
            uv = (vert + vec2(1, 1)) * 0.5;
        }
    ''',
    fragment_shader='''
        #version 130

        varying vec2 uv;
        uniform sampler2D diffuse;
        out vec3 f_color;

        void main() {
            f_color = texture(diffuse, uv).rgb;
            //f_color = vec3(uv, 0);
        }
    ''',
)

verts = np.array([
    (-1, -1),
    (+1, -1),
    (-1, +1),
    (+1, +1),
])
texcoords = np.array([
    (0, 0),
    (1, 0),
    (1, 1),
    (0, 1)
])
all_attrs = np.concatenate([verts, texcoords], axis=1).astype('f4')
lights_quad = mgl.buffer(verts.astype('f4').tobytes())
vao = mgl.simple_vertex_array(
    lights_shader,
    lights_quad,
    'vert',
)


rock = pyglet.sprite.Sprite(
    pyglet.resource.image('sprites/rock_sm.png')
)
rock.scale = max(
    WIDTH / rock.width,
    HEIGHT / rock.height
)



water_verts = mgl.buffer(reserve=8, dynamic=True)
water_shader = mgl.program(
    vertex_shader='''
        #version 130

        in vec2 vert;

        uniform mat4 mvp;
        varying vec2 uv;

        void main() {
            gl_Position = mvp * vec4(vert, 0.0, 1.0);
            uv = (gl_Position.xy + vec2(1, 1)) * 0.5;
        }
    ''',
    fragment_shader='''
        #version 130

        varying vec2 uv;
        uniform float t;
        uniform sampler2D diffuse;
        out vec3 f_color;

        void main() {
            vec2 off = vec2(
                sin(sin(60.0 * uv.x) + cos(uv.y) * t),
                sin(sin(60.0 * uv.y + 1.23) + (0.5 + 0.5 * sin(uv.x)) * t)
            ) * 0.005;
            vec3 diff = texture(diffuse, uv + off).rgb;
            f_color = diff * 0.55 + vec3(0.1, 0.15, 0.2);
        }
    ''',
)
water_vao = mgl.simple_vertex_array(
    water_shader,
    water_verts,
    'vert',
)

from pyrr import Matrix44


t = 0


@window.event
def on_draw():
    global water_verts, water_vao, t
    # Update graphical things
    dt = 1 / 60
    t += dt
    pc.update(dt)
    for f in flies:
        f.update(dt)

    for w in water:
        w.update(dt)

    window.clear()

    fbuf.use()
    fbuf.clear(0.13, 0.1, 0.1)
    gl.glLoadIdentity()
    gl.glScalef(PIXEL_SCALE, PIXEL_SCALE, 1)
    rock.draw()
    sprites.draw()

    mgl.screen.use()
    mgl.screen.clear()
    fbuf.color_attachments[0].use()
    vao.render(moderngl.TRIANGLE_STRIP)

    #gl.glUseProgram(water_shader.glo)

    view = Matrix44.orthogonal_projection(
        0, WIDTH * SPACE_SCALE,
        0, HEIGHT * SPACE_SCALE,
        -1, 1,
        dtype='f4'
    )
    all_water = np.concatenate(*[w.vertices for w in water]).reshape(-1, 1)
    all_water = all_water.astype('f4').tobytes()

    if water_verts.size != len(all_water):
        water_verts = mgl.buffer(all_water, dynamic=True)
        water_vao = mgl.simple_vertex_array(
            water_shader,
            water_verts,
            'vert',
        )
    else:
        water_verts.write(all_water)
    water_shader.get('mvp', None).write(view.tobytes())
    water_shader.get('t', None).value = t
    fbuf.color_attachments[0].use()
    water_vao.render(moderngl.TRIANGLE_STRIP)
    gl.glUseProgram(0)

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


def screenshot_path(comp_start=datetime.date(2019, 3, 24)):
    """Get a path to save a screenshot into."""
    today = datetime.date.today()
    comp_day = (today - comp_start).days + 1
    grabs = pathlib.Path('grabs')

    for n in count(1):
        p = grabs / f'day{comp_day}-{n}.png'
        if not p.exists():
            return str(p)


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

    if symbol == key.F12:
        # disable transfer alpha channel
        gl.glPixelTransferf(gl.GL_ALPHA_BIAS, 1.0)
        image = pyglet.image.ColorBufferImage(
            0,
            0,
            window.width,
            window.height
        )
        image.save(screenshot_path())
        # re-enable alpha channel transfer
        gl.glPixelTransferf(gl.GL_ALPHA_BIAS, 0.0)

    keys_down.on_key_press(symbol, modifiers)


def update_physics(dt):
    for _ in range(3):
        space.step(1 / 180)

pyglet.clock.set_fps_limit(60)
pyglet.clock.schedule(update_physics)
pyglet.app.run()

