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
from wtf.water import Water, WaterBatch
from wtf.geom import SPACE_SCALE, phys_to_screen
from wtf.actors import actor_sprites, Frog, Fly
from wtf.hud import HUD


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

water(6.5)
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


water_batch = WaterBatch(mgl)


def on_draw(dt):
    # Update graphical things
    pc.update(dt)
    for f in Fly.insts:
        f.update(dt)

    for w in Water.insts:
        w.update(dt)

    hud.update(dt)

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

    mvp = Matrix44.orthogonal_projection(
        0, WIDTH * SPACE_SCALE,
        0, HEIGHT * SPACE_SCALE,
        -1, 1,
        dtype='f4'
    )

    fbuf.color_attachments[0].use()
    water_batch.render(dt, mvp)
    gl.glUseProgram(0)

    hud.draw()

    fps_display.draw()


class JumpController:
    """Control the frog's jumps.

    We track which jumps the frog has available.

    """
    IMPULSE_SCALE = 26
    JUMP_IMPULSES = {
        Direction.UL: Vec2d.unit().rotated_degrees(30) * IMPULSE_SCALE,
        Direction.U: Vec2d.unit() * IMPULSE_SCALE,
        Direction.UR: Vec2d.unit().rotated_degrees(-30) * IMPULSE_SCALE,
        Direction.DL: Vec2d.unit().rotated_degrees(180 - 30) * IMPULSE_SCALE,
        Direction.D: Vec2d.unit().rotated_degrees(180) * IMPULSE_SCALE,
        Direction.DR: Vec2d.unit().rotated_degrees(180 + 30) * IMPULSE_SCALE,
    }

    def __init__(self, pc, hud):
        self.hud = hud
        self.reset()

    def reset(self):
        """Set all directions back to available."""
        self.available = dict.fromkeys(Direction, True)
        for d in Direction:
            self.hud.set_available(d, True)

    def jump(self, direction):
        """Request a jump in the given direction."""
        if self.available[direction]:
            pc.body.velocity = self.JUMP_IMPULSES[direction]
            self.available[direction] = False
            self.hud.set_available(direction, False)
        else:
            self.hud.warn_unavailable(direction)


hud = HUD(WIDTH, HEIGHT)
controls = JumpController(pc, hud)


keyhandler = wtf.keys.KeyInputHandler(
    jump=controls.jump,
    window=window,
)
window.push_handlers(keyhandler)


def update_physics(dt):
    for _ in range(3):
        space.step(1 / 180)


pyglet.clock.set_fps_limit(60)
pyglet.clock.schedule(on_draw)
pyglet.clock.schedule(update_physics)
pyglet.app.run()
