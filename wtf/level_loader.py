import numpy as np
import math
import re
import pyglet.resource
from xml.etree.ElementTree import parse
from pymunk import Vec2d

from .sprites import load_centered
from .water import Water
from .geom import SPACE_SCALE, phys_to_screen
from .poly import RockPoly
from .actors import Butterfly, Fly, Frog, Fish, Goldfish
from .scenery import Platform, Lilypad


COMMA_WSP = re.compile(r'(?:\s+,?\s*|,\s*)')


def path_toks(path):
    """Iterate over components of path as tokens."""
    toks = COMMA_WSP.split(path)
    for tok in toks:
        if not tok:
            continue
        elif tok.isalpha():
            yield tok
        else:
            try:
                v = float(tok)
            except ValueError:
                raise ValueError(
                    f"Couldn't parse {tok!r} from {path!r}"
                )
            yield v


def parse_path(path_str):
    verts = []
    path = []
    pos = Vec2d(0, 0)

    toks = path_toks(path_str)

    next = toks.__next__

    def line():
        path.append(tuple(pos))

    op = 'l'
    for tok in toks:
        if isinstance(tok, str):
            if tok in ('m', 'M'):
                if path:
                    verts.append(path)
                    path = []
                v = Vec2d(next(), next())
                if tok == 'M':
                    pos = v
                    op = 'L'
                else:
                    pos += v
                    op = 'l'
                line()
            elif op in ('z', 'Z'):
                pos = path[0]
                line()
                verts.append(path)
                path = []
            else:
                op = tok
                continue
        else:
            if op == 'l':
                pos += Vec2d(tok, next())
                line()
            elif op == 'L':
                pos = Vec2d(tok, next())
                line()
            elif op == 'H':
                pos.x = tok
                line()
            elif op == 'h':
                pos.x += tok
                line()
            elif op == 'V':
                pos.y = tok
                line()
            elif op == 'v':
                pos.y += tok
                line()
            elif op == 'c':
                for _ in range(3):
                    next()
                pos += Vec2d(next(), next())
                line()
            elif op == 'C':
                for _ in range(3):
                    next()
                pos = Vec2d(next(), next())
                line()
            else:
                raise ValueError(f"Unknown path op {op}")
    if path:
        verts.append(path)
    return verts


class NoSuchLevel(Exception):
    """Raised when the level name does not exist."""


SVG_SCALE = 2 * SPACE_SCALE


def load_level(level):
    try:
        f = pyglet.resource.file(f'levels/{level.name}.svg')
    except pyglet.resource.ResourceNotFoundException:
        raise NoSuchLevel(f"Level {level.name} does not exist")
    doc = parse(f)
    height = float(doc.getroot().attrib['height'])
    for path in doc.findall('.//{http://www.w3.org/2000/svg}path'):
        for loop in parse_path(path.attrib['d']):
            verts = np.array(
                [(x, (height - y)) for x, y in loop],
            )
            style = path.attrib.get('style', '')
            mo = re.search(r'(?:[; ]|^)fill *: *([^;]+)(?:;|$)', style)
            if mo:
                fill = mo.group(1)
            else:
                fill = 'none'
            draw = fill and fill != 'none'
            if fill.startswith('#'):
                color = int(fill[1:7], 16)
                color, b = divmod(color, 256)
                r, g = divmod(color, 256)
                color = np.array([r, g, b]) / 255
            else:
                color = (0.5, 0.4, 0.3)

            level.objs.append(
                RockPoly(
                    verts.reshape(-1) * SVG_SCALE,
                    draw=draw,
                    color=color,
                )
            )

    for r in doc.findall('.//{http://www.w3.org/2000/svg}rect'):
        x1 = float(r.attrib['x']) * SVG_SCALE
        y = (height - float(r.attrib['y'])) * SVG_SCALE
        x2 = x1 + float(r.attrib['width']) * SVG_SCALE
        y_bot = y - float(r.attrib['height']) * SVG_SCALE
        assert y > y_bot
        Water(y, x1, x2, y_bot)

    load_entities(doc, level)


ACTOR_TYPES = {
    'butterfly': Butterfly,
    'fly': Fly,
    'goldfish': Goldfish,
    'fish': Fish,
    'lilypad': Lilypad,
}


def xform_matrix(a, b, c, d, e, f):
    return np.array([
        [a, c, e],
        [b, d, f],
        [0, 0, 1],
    ])


def xform_scale(x, y=None):
    if y is None:
        y = x
    return np.array([
        [x, 0, 0],
        [0, y, 0],
        [0, 0, 1],
    ])


TRANSFORMS = {
    'matrix': xform_matrix,
    'scale': xform_scale,
}


def load_entities(doc, level):
    height = float(doc.getroot().attrib['height'])

    imgs = {}

    for r in doc.findall('.//{http://www.w3.org/2000/svg}image'):
        href = r.attrib['{http://www.w3.org/1999/xlink}href']

        mo = re.search(r'/([^/]+)/([^/]+)\.(png|jpg)$', href)
        if not mo:
            print(f"No match for {href}")
            continue

        group, name, ext = mo.groups()
        if group == 'backgrounds':
            continue

        rot = 0
        scale = 1
        flip = False

        cx = float(r.attrib['x']) + float(r.attrib['width']) * 0.5
        cy = float(r.attrib['y']) + float(r.attrib['height']) * 0.5
        try:
            transform = r.attrib['transform']
        except KeyError:
            pass
        else:
            mat = eval(transform, TRANSFORMS)
            a = mat @ np.array([
                [cx, cy, 1],
                [1, 0, 0],
                [0, 1, 0],
            ]).T
            cx, cy = a[:2, 0]
            flip = np.cross(a[..., 1], a[..., 2])[2] < 0
            x1, x2, _ = a[..., 1]
            rot = math.degrees(math.atan2(x2, x1))
            scale = math.hypot(x1, x2)

        w = float(r.attrib['width']) * SVG_SCALE
        h = float(r.attrib['height']) * SVG_SCALE

        # Convert to screen coords
        cx = cx * SVG_SCALE
        cy = (height - cy) * SVG_SCALE

        if group == 'scenery':
            k = f'scenery/{name}.{ext}'
            try:
                img = imgs[k]
            except KeyError:
                img = imgs[k] = load_centered(name, group)

            s = pyglet.sprite.Sprite(img, batch=level.fg_batch)
            s.position = phys_to_screen(cx, cy)
            s.rotation = rot
            scale = float(r.attrib['width']) * scale / img.width * 2
            s.scale = scale
            if flip:
                s.scale_y = -1
            level.objs.append(s)
            continue

        cls = ACTOR_TYPES.get(name)
        if cls:
            level.actors.append(cls(cx, cy))
            continue
        elif 'jumper.png' in href:
            frog = level.pc = Frog(cx, cy)
            level.actors.append(frog)
        elif 'platform.png' in href:
            level.objs.append(
                Platform(cx - w // 2, cy - h // 2)
            )
