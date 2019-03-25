import random
from math import sin

from pyglet import gl
import pyglet.resource
import pyglet.graphics
import pyglet.sprite
import pymunk
from pymunk import Vec2d

from .geom import phys_to_screen, SPACE_SCALE
from .physics import (
    space, box, COLLISION_TYPE_FROG, COLLISION_TYPE_COLLECTIBLE
)


actor_sprites = pyglet.graphics.Batch()


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

        self.dl = actor_sprites.add(
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
    SPRITE.anchor_y = 5

    def __init__(self, x, y):
        self.sprite = pyglet.sprite.Sprite(self.SPRITE, batch=actor_sprites)
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


class Fly:
    SPRITE = pyglet.resource.image('sprites/fly.png')
    SPRITE.anchor_x = SPRITE.width // 2
    SPRITE.anchor_y = SPRITE.height // 3

    CATCH_RADIUS = 2.5

    insts = []

    def __init__(self, x, y):
        self.pos = Vec2d(x + 0.5, y + 0.5)
        self.t = 0
        self.sprite = pyglet.sprite.Sprite(
            self.SPRITE,
            batch=actor_sprites,
            usage='stream'
        )
        self.sprite.position = phys_to_screen(self.pos)

        self.shape = pymunk.Circle(
            space.static_body,
            self.CATCH_RADIUS,
            offset=(x, y)
        )
        self.shape.collision_type = COLLISION_TYPE_COLLECTIBLE
        self.shape.obj = self
        space.add(self.shape)
        self.update(random.uniform(0, 5))
        self.insts.append(self)

    def update(self, dt):
        self.t += dt
        self.sprite._scale_y *= -1
        self.sprite._rotation = 10 * sin(self.t)
        self.sprite._x, self.sprite._y = phys_to_screen(
            self.pos
            + Vec2d(
                0.5 * sin(2 * self.t),
                0.5 * sin(3 * self.t)
            )  # lissajous wander
        )
        self.sprite._update_position()

    def collect(self):
        """Called when this Fly is collected."""
        self.delete()

    def delete(self):
        """Delete this instance."""
        self.insts.remove(self)
        self.sprite.delete()
        space.remove(self.shape)
