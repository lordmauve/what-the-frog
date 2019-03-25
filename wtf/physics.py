import pymunk
from pymunk import Vec2d


GRAVITY = Vec2d(0, -50)
BUOYANCY = Vec2d(0, 500)
WATER_DRAG = 20

space = pymunk.Space()
space.gravity = GRAVITY


# Collision types for callbacks
COLLISION_TYPE_WATER = 1
COLLISION_TYPE_COLLECTIBLE = 2
COLLISION_TYPE_FROG = 3


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
