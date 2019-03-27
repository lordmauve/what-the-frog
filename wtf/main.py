import pyglet
from pyglet import gl
import pyglet.sprite
import pyglet.resource
from pymunk.vec2d import Vec2d
import moderngl
from pyrr import Matrix44
from pyglet.window import key
from pyglet.event import EVENT_UNHANDLED, EVENT_HANDLED

import wtf.keys
from wtf.directions import Direction
from wtf.physics import (
    space, COLLISION_TYPE_FROG, COLLISION_TYPE_COLLECTIBLE,
    create_walls
)
from wtf.water import Water, WaterBatch
from wtf.geom import SPACE_SCALE
from wtf.actors import actor_sprites, Frog, Fly
from wtf.hud import HUD
from wtf.offscreen import OffscreenBuffer
from wtf.poly import RockPoly


WIDTH = 1600   # Width in hidpi pixels
HEIGHT = 1200  # Height in hidpi pixels

PIXEL_SCALE = 1.0  # Scale down for non-hidpi screens


window = pyglet.window.Window(
    width=round(WIDTH * PIXEL_SCALE),
    height=round(HEIGHT * PIXEL_SCALE)
)


mgl = moderngl.create_context()


def water(y, x1=0, x2=WIDTH * SPACE_SCALE, bot_y=0):
    return Water(y, x1, x2, bot_y)


def on_collect(arbiter, space, data):
    """Called when a collectible is hit"""
    fly, frog = arbiter.shapes
    frog.obj.lick(fly.obj.sprite.position)
    fly.obj.collect(frog, controls)
    space.remove(fly)
    if not Fly.insts:
        level.win()
    return False


handler = space.add_collision_handler(
    COLLISION_TYPE_COLLECTIBLE,
    COLLISION_TYPE_FROG
)
handler.begin = on_collect


class Level:
    def __init__(self, name='level1'):
        self.name = name
        self.won = None
        self.create()
        if self.pc is None:
            self.pc = Frog(6, 7)

    def win(self, *_):
        if self.won is not None:
            return
        self.won = True
        hud.show_card('3star')

    def fail(self, *_):
        if self.won is not None:
            return
        self.won = False

        flies_remaining = len(Fly.insts)
        if flies_remaining == 1:
            hud.show_card('2star')
        elif flies_remaining == 2:
            hud.show_card('1star')
        else:
            hud.show_card('fail')

    def create(self):
        from wtf.level_loader import load_level
        self.won = None
        self.pc = None
        self.objs = []
        self.static_shapes = create_walls(space, WIDTH, HEIGHT)
        load_level(self)

    def reload(self):
        self.delete()
        self.create()

    def __del__(self):
        self.delete()

    def delete(self):
        for o in self.objs:
            try:
                o.delete()
            except KeyError:
                raise KeyError(f"Couldn't delete {o}")
        for f in Fly.insts[:]:
            f.delete()
        for w in Water.insts[:]:
            w.delete()
        self.pc.delete()
        self.pc = None
        space.remove(*self.static_shapes)
        assert not space.bodies, f"Space contains bodies: {space.bodies}"
        assert not space.shapes, f"Space contains shapes: {space.shapes}"


fps_display = pyglet.clock.ClockDisplay()


offscreen = OffscreenBuffer(WIDTH, HEIGHT, mgl)

background = pyglet.sprite.Sprite(
    pyglet.resource.image('backgrounds/level1.png')
)


water_batch = WaterBatch(mgl)

level = Level()


def on_draw(dt):
    # Update graphical things
    level.pc.update(dt)

    for f in Fly.insts:
        f.update(dt)

    for w in Water.insts:
        w.update(dt)

    hud.update(dt)

    window.clear()

    with offscreen.bind_buffer() as fbuf:
        fbuf.clear(0.13, 0.1, 0.1)
        gl.glLoadIdentity()
        gl.glScalef(PIXEL_SCALE, PIXEL_SCALE, 1)
        background.draw()
        RockPoly.batch.draw()
        actor_sprites.draw()

    mgl.screen.clear()
    offscreen.draw()

    mvp = Matrix44.orthogonal_projection(
        0, WIDTH * SPACE_SCALE,
        0, HEIGHT * SPACE_SCALE,
        -1, 1,
        dtype='f4'
    )

    with offscreen.bind_texture():
        water_batch.render(dt, mvp)
    gl.glUseProgram(0)

    hud.draw()

#    fps_display.draw()


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
        self.pc = pc
        self.hud = hud
        self.available = None
        self.reset()

    def reset(self):
        """Set all directions back to available."""
        if self.available and not any(self.available.values()):
            pyglet.clock.unschedule(level.fail)
        self.available = dict.fromkeys(Direction, True)
        for d in Direction:
            self.hud.set_available(d, True)

    def all_available(self):
        """return True if all directions are available."""
        return all(self.available.values())

    def jump(self, direction):
        """Request a jump in the given direction."""
        if self.available[direction]:
            self.pc.body.velocity = self.JUMP_IMPULSES[direction]
            self.available[direction] = False
            self.hud.set_available(direction, False)
            if not any(self.available.values()):
                pyglet.clock.schedule_once(level.fail, 3)
        else:
            self.hud.warn_unavailable(direction)


hud = HUD(WIDTH, HEIGHT)
controls = JumpController(level.pc, hud)


keyhandler = wtf.keys.KeyInputHandler(
    jump=controls.jump,
    window=window,
)
window.push_handlers(keyhandler)


def on_key_press(symbol, modifiers):
    if symbol == key.ESCAPE:
        if controls.all_available():
            pyglet.clock.unschedule(on_draw)
            pyglet.clock.unschedule(update_physics)
            pyglet.app.exit()
            return EVENT_HANDLED
        level.reload()
        controls.reset()
        controls.pc = level.pc
        return EVENT_HANDLED
    return EVENT_UNHANDLED


window.push_handlers(on_key_press)


def update_physics(dt):
    if level.won is not None:
        return

    for _ in range(3):
        space.step(1 / 180)


def run():
    pyglet.clock.set_fps_limit(60)
    pyglet.clock.schedule(on_draw)
    pyglet.clock.schedule(update_physics)
    pyglet.app.run()
