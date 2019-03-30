import random
from math import sin, cos, copysign

from pyglet import gl
import pyglet.resource
import pyglet.graphics
import pyglet.sprite
import pyglet.image
import pymunk
from pymunk import Vec2d

from .geom import phys_to_screen, SPACE_SCALE
from .physics import (
    space, cbox, COLLISION_TYPE_FROG, COLLISION_TYPE_COLLECTIBLE
)
from .sprites import load_centered, center
from .state import UnderwaterState


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
    SPRITE = load_centered('jumper')

    # How long it takes to lick, in seconds
    TONGUE_SPEED = 0.2  # seconds

    def __init__(self, x, y):
        self.sprite = pyglet.sprite.Sprite(self.SPRITE, batch=actor_sprites)
        self.sprite.position = phys_to_screen(x, y)
        self.body = pymunk.Body(5, pymunk.inf)
        self.body.position = (x, y)

        # Updated by water collision handler
        self.body.underwater = UnderwaterState.DRY

        self.shape = cbox(
            self.body,
            0, 0,
            w=self.SPRITE.width * SPACE_SCALE,
            h=self.SPRITE.height * SPACE_SCALE,
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
        else:
            self.tongue = Tongue(self.mouth_pos, pos)
            self.tongue.t = 0

    @property
    def mouth_pos(self):
        return Vec2d(*self.sprite.position)

    def update(self, dt):
        self.sprite.position = self.body.position / SPACE_SCALE

        # Update the tongue
        if self.tongue:
            self.tongue.t += dt / self.TONGUE_SPEED
            t = self.tongue.t
            if t >= 1.0:
                self.tongue.delete()
                self.tongue = None
            else:
                self.tongue.length = 4.0 * t * (1.0 - t)
                self.tongue.mouth_pos = self.mouth_pos
                self.tongue.recalc_verts()

    def delete(self):
        if self.tongue:
            self.tongue.delete()
        self.sprite.delete()
        space.remove(self.body, self.shape)


class SpriteAnim:
    """Animation that is not tied directly to Pyglet's clock."""

    def __init__(self, sprite, seq, rate=1 / 20):
        self.sprite = sprite
        self.seq = seq
        self.rate = rate

        self.frame = 0
        self.t = 0

    def update(self, dt):
        self.t += dt
        f, self.t = divmod(self.t, self.rate)
        self.frame = (self.frame + int(f)) % len(self.seq)
        self.sprite.image = self.seq[self.frame]


class Fly:
    DIMS = (1, 4)
    SPRITE = pyglet.resource.image('sprites/fly.png')
    SEQ = center(pyglet.image.ImageGrid(SPRITE, *DIMS).get_texture_sequence())
    RATE = 0.05

    CATCH_RADIUS = 2

    insts = []

    def __init__(self, x, y):
        self.pos = Vec2d(x + 0.5, y + 0.5)
        self.t = 0
        self.sprite = pyglet.sprite.Sprite(
            self.SEQ[0],
            batch=actor_sprites,
            usage='stream'
        )
        self.sprite_anim = SpriteAnim(self.sprite, self.SEQ, self.RATE)

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

    def wander(self, t):
        """Return a small lissajous wander."""
        vx = cos(2 * t)
        self.sprite._scale_x = copysign(1, vx)
        return Vec2d(
            0.5 * sin(2 * t),
            0.5 * sin(3 * t)
        )

    def update(self, dt):
        self.sprite_anim.update(dt)
        self.t += dt
        self.sprite.update(
            *phys_to_screen(self.pos + self.wander(self.t)),
            rotation=10 * sin(self.t),
        )

    def collect(self, pc, controls):
        """Called when this Fly is collected."""
        self.delete()

    def delete(self):
        """Delete this instance."""
        self.insts.remove(self)
        self.sprite.delete()
        space.remove(self.shape)

    @classmethod
    def freeze_all(cls):
        clock = pyglet.app.event_loop.clock
        for f in cls.insts:
            if f.sprite._animation:
                clock.unschedule(f.sprite._animate)


class Butterfly(Fly):
    DIMS = (1, 6)
    SPRITE = pyglet.resource.image('sprites/butterfly.png')
    SEQ = center(pyglet.image.ImageGrid(SPRITE, *DIMS).get_texture_sequence())
    RATE = 0.1

    COLORS = [
        (211, 167, 29),
        (21, 115, 154),
        (154, 52, 21),
    ]

    def __init__(self, x, y):
        super().__init__(x, y)

        # Pick a color at random but always the same color for the
        # same level
        hsh = hash((round(x), round(y)))
        self.sprite.color = self.COLORS[hsh % len(self.COLORS)]

    def collect(self, pc, controls):
        """Replenish jumps when the Butterfly is collected."""
        controls.reset()
        super().collect(pc, controls)


class Fish(Fly):
    SPRITE = center(pyglet.resource.image('sprites/fish.png'))
    SEQ = [SPRITE]

    CATCH_RADIUS = 2

    def wander(self, t):
        """Return a small lissajous wander."""
        xperiod = 0.3
        sx = sin(xperiod * t)
        px = sx * abs(sx)

        vx = cos(xperiod * t)
        self.sprite._scale_x = copysign(max(0.3, abs(vx)), vx)
        return Vec2d(
            1.5 * px,
            0.2 * sin(0.2 * t),
        )


class Goldfish(Fish):
    SPRITE = center(pyglet.resource.image('sprites/goldfish.png'))
    SEQ = [SPRITE]

    def collect(self, pc, controls):
        """Replenish jumps when this Goldfish is collected."""
        controls.reset()
        super().collect(pc, controls)
