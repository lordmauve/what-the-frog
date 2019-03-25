from pymunk import Vec2d


# Space units are 64 screen pixels
SPACE_SCALE = 1 / 64


def phys_to_screen(v, v2=None):
    if v2:
        return Vec2d(v, v2) / SPACE_SCALE
    return Vec2d(*v) / SPACE_SCALE


def screen_to_phys(v, v2=None):
    if v2:
        return Vec2d(v, v2) * SPACE_SCALE
    return Vec2d(*v) * SPACE_SCALE
