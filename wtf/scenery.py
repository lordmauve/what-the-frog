import math

import pymunk
import pyglet.resource
import pyglet.sprite
import pyglet.graphics

from .geom import phys_to_screen, SPACE_SCALE
from .sprites import load_centered
from .physics import box, space, cbox
from .actors import actor_sprites


class Scenery:
    batch = pyglet.graphics.Batch()

    # Dimensions of the object in physics coordinates
    DIMS = 1, 1

    # Friction amount, higher is more force
    FRICTION = 1.0

    # Elasticity, higher is more bouncy
    ELASTICITY = 0.6

    def __init__(self, x, y):
        """Create a scenery object.

        Here x and y are in physics coordinates.

        """
        self.sprite = pyglet.sprite.Sprite(self.SPRITE, batch=actor_sprites)
        self.sprite.position = phys_to_screen(x, y)

        shape = box(
            space.static_body,
            x, y, *self.DIMS
        )
        shape.friction = self.FRICTION
        shape.elasticity = self.ELASTICITY
        space.add(shape)
        self.shape = shape

    def delete(self):
        self.sprite.delete()
        space.remove(self.shape)


class Platform(Scenery):
    SPRITE = pyglet.resource.image('sprites/platform.png')
    DIMS = (3, 1)


class Lilypad(Scenery):
    SPRITE = load_centered('lilypad')
    SPRITE.anchor_y = SPRITE.height * 0.78

    def __init__(self, x, y):
        y += 1
        self.sprite = pyglet.sprite.Sprite(self.SPRITE, batch=actor_sprites)
        self.sprite.position = phys_to_screen(x, y)

        self.body = pymunk.Body(10, pymunk.inf)
        self.body.position = (x, y)
        self.shape = cbox(
            self.body,
            0, 0,
            w=self.SPRITE.width * SPACE_SCALE,
            h=20 * SPACE_SCALE,
        )
        self.shape.obj = self
        self.shape.friction = self.FRICTION
        self.shape.elasticity = self.ELASTICITY

        space.add(self.body, self.shape)

    def update(self, dt):
        self.sprite.position = self.body.position / SPACE_SCALE
        self.sprite.rotation = math.degrees(self.body.angle)

    def delete(self):
        self.sprite.delete()
        space.remove(self.body, self.shape)
