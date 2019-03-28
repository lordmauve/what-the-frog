import pymunk
from pymunk import Vec2d

from .geom import SPACE_SCALE


GRAVITY = Vec2d(0, -50)
BUOYANCY = Vec2d(0, 500)
WATER_DRAG = 20

space = pymunk.Space()
space.gravity = GRAVITY


# Collision types for callbacks
COLLISION_TYPE_WATER = 1
COLLISION_TYPE_COLLECTIBLE = 2
COLLISION_TYPE_FROG = 3


def cbox(body, x, y, w, h):
    """Create a box centered at x, y."""
    return box(body, x - w * 0.5, y - h * 0.5, w, h)


def box(body, x, y, w, h):
    """Create a pymunk box, with the bottom-left at x, y."""
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


def create_walls(space, width, height):
    walls = [
        ((-5, -5), (width + 5, -5)),
        ((-5, -5), (-5, height + 5)),
        ((-5, height + 5), (width + 5, height + 5)),
        ((width + 5, -5), (width + 5, height + 5)),
    ]
    shapes = []
    for a, b in walls:
        a = Vec2d(*a) * SPACE_SCALE
        b = Vec2d(*b) * SPACE_SCALE
        shape = pymunk.Segment(space.static_body, a, b, 10 * SPACE_SCALE)
        shape.friction = 0
        shape.elasticity = 0.6
        space.add(shape)
        shapes.append(shape)
    return shapes
