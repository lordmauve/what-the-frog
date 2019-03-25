import pyglet
from pyglet import gl
import pyglet.sprite
import pyglet.resource
import pymunk
from pymunk.vec2d import Vec2d
import moderngl
import numpy as np
from pyrr import Matrix44

import wtf.keys
from wtf.directions import Direction
from wtf.physics import (
    space, box, COLLISION_TYPE_FROG, COLLISION_TYPE_COLLECTIBLE
)
from wtf.water import Water
from wtf.geom import SPACE_SCALE, phys_to_screen
from wtf.actors import actor_sprites, Frog, Fly


WIDTH = 1600   # Width in hidpi pixels
HEIGHT = 1200  # Height in hidpi pixels

PIXEL_SCALE = 1.0  # Scale down for non-hidpi screens


window = pyglet.window.Window(
    width=round(WIDTH * PIXEL_SCALE),
    height=round(HEIGHT * PIXEL_SCALE)
)


mgl = moderngl.create_context()

platform = pyglet.resource.image('sprites/platform.png')
platforms = []


def create_platform(x, y):
    """Create a platform.

    Here x and y are in physics coordinates.

    """
    s = pyglet.sprite.Sprite(platform, batch=actor_sprites)
    s.position = phys_to_screen(x, y)
    platforms.append(s)

    shape = box(
        space.static_body,
        x, y, 3, 1
    )
    shape.friction = 0.6
    shape.elasticity = 0.6
    space.add(shape)


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


def water(y, x1=0, x2=WIDTH * SPACE_SCALE, bot_y=0):
    return Water(y, x1, x2, bot_y)


def on_collect(arbiter, space, data):
    """Called when a collectible is hit"""
    fly, frog = arbiter.shapes
    frog.obj.lick(fly.obj.sprite.position)
    fly.obj.collect()
    space.remove(fly)
    return False


handler = space.add_collision_handler(
    COLLISION_TYPE_COLLECTIBLE,
    COLLISION_TYPE_FROG
)
handler.begin = on_collect


pc = Frog(6, 7)
create_platform(-1, 7)
create_platform(5, 6)
create_platform(5, 17)
create_platform(13, 9)
create_walls(space)

water = [
    water(6.5),
]

Fly(3, 10)
Fly(16, 16)


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
        in float depth;

        uniform mat4 mvp;
        varying vec2 uv;
        varying vec2 refl_uv;
        varying float vdepth;

        vec2 uv_pos(vec4 position) {
            return (position.xy + vec2(1, 1)) * 0.5;
        }

        void main() {
            gl_Position = mvp * vec4(vert, 0.0, 1.0);
            uv = uv_pos(gl_Position);

            vdepth = depth;
            refl_uv = uv_pos(mvp * vec4(vert.x, vert.y + 2 * depth, 0, 1.0));
        }
    ''',
    fragment_shader='''
        #version 130

        varying vec2 uv;
        varying vec2 refl_uv;
        varying float vdepth;
        uniform float t;
        uniform sampler2D diffuse;
        out vec3 f_color;

        void main() {
            vec2 off = vec2(
                sin(sin(60.0 * uv.x) + cos(uv.y) * t),
                sin(sin(60.0 * uv.y + 1.23) + (0.5 + 0.5 * sin(uv.x)) * t)
            ) * 0.005;
            vec3 diff = texture(diffuse, uv + off).rgb;
            float refl_amount = 0.6 / (pow(vdepth * 2, 2) + 1);

            vec3 refl_diff = texture(diffuse, refl_uv).rgb;

            f_color = diff * 0.55 + vec3(0.1, 0.15, 0.2)
                      + refl_diff * refl_amount;
        }
    ''',
)
water_vao = mgl.simple_vertex_array(
    water_shader,
    water_verts,
    'vert',
    'depth',
)


t = 0


@window.event
def on_draw():
    global water_verts, water_vao, t
    # Update graphical things
    dt = 1 / 60
    t += dt
    pc.update(dt)
    for f in Fly.insts:
        f.update(dt)

    for w in water:
        w.update(dt)

    window.clear()

    fbuf.use()
    fbuf.clear(0.13, 0.1, 0.1)
    gl.glLoadIdentity()
    gl.glScalef(PIXEL_SCALE, PIXEL_SCALE, 1)
    rock.draw()
    actor_sprites.draw()

    mgl.screen.use()
    mgl.screen.clear()
    fbuf.color_attachments[0].use()
    vao.render(moderngl.TRIANGLE_STRIP)

    view = Matrix44.orthogonal_projection(
        0, WIDTH * SPACE_SCALE,
        0, HEIGHT * SPACE_SCALE,
        -1, 1,
        dtype='f4'
    )
    all_water = np.concatenate([w.vertices for w in water])
    depths = np.stack([
        np.zeros(len(all_water) // 2),
        all_water[::2, 1] - all_water[1::2, 1]
    ], axis=1).reshape((-1, 1))
    all_water = np.concatenate([all_water, depths], axis=1)
    all_water = all_water.reshape(-1).astype('f4').tobytes()

    if water_verts.size != len(all_water):
        water_verts = mgl.buffer(all_water, dynamic=True)
        water_vao = mgl.simple_vertex_array(
            water_shader,
            water_verts,
            'vert',
            'depth',
        )
    else:
        water_verts.write(all_water)
    water_shader.get('mvp', None).write(view.tobytes())
    water_shader.get('t', None).value = t
    fbuf.color_attachments[0].use()
    water_vao.render(moderngl.TRIANGLE_STRIP)
    gl.glUseProgram(0)

    fps_display.draw()


IMPULSE_SCALE = 26
JUMP_IMPULSES = {
    Direction.UL: Vec2d.unit().rotated_degrees(30) * IMPULSE_SCALE,
    Direction.U: Vec2d.unit() * IMPULSE_SCALE,
    Direction.UR: Vec2d.unit().rotated_degrees(-30) * IMPULSE_SCALE,
    Direction.DL: Vec2d.unit().rotated_degrees(180 - 30) * IMPULSE_SCALE,
    Direction.D: Vec2d.unit().rotated_degrees(180) * IMPULSE_SCALE,
    Direction.DR: Vec2d.unit().rotated_degrees(180 + 30) * IMPULSE_SCALE,
}


def jump(direction):
    pc.body.velocity = JUMP_IMPULSES[direction]


keyhandler = wtf.keys.KeyInputHandler(
    jump=jump,
    window=window,
)
window.push_handlers(keyhandler)


def update_physics(dt):
    for _ in range(3):
        space.step(1 / 180)


pyglet.clock.set_fps_limit(60)
pyglet.clock.schedule(update_physics)
pyglet.app.run()
