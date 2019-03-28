import pyglet.resource
import pyglet.sprite
import pyglet.graphics

from .geom import phys_to_screen
from .physics import box, space
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
