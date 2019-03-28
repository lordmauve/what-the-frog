import numpy as np
import re
import pyglet.resource
from xml.etree.ElementTree import parse
from pymunk import Vec2d

from .water import Water
from .geom import SPACE_SCALE
from .poly import RockPoly
from .actors import Butterfly, Fly, Frog, Fish, Goldfish
from .scenery import Platform


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
            elif tok == 'H':
                pos.x = tok
                line()
            elif tok == 'h':
                pos.x += tok
                line()
            elif tok == 'V':
                pos.y = tok
                line()
            elif tok == 'v':
                pos.y += tok
                line()
    if path:
        verts.append(path)
    return verts


class NoSuchLevel(Exception):
    """Raised when the level name does not exist."""


def load_level(level):
    scale = 2 * SPACE_SCALE
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
            level.objs.append(
                RockPoly(
                    verts.reshape(-1) * scale,
                    draw='fill:none' not in path.attrib.get('style')
                )
            )

    for r in doc.findall('.//{http://www.w3.org/2000/svg}rect'):
        x1 = float(r.attrib['x']) * scale
        y = (height - float(r.attrib['y'])) * scale
        x2 = x1 + float(r.attrib['width']) * scale
        y_bot = y - float(r.attrib['height']) * scale
        assert y > y_bot
        Water(y, x1, x2, y_bot)

    for r in doc.findall('.//{http://www.w3.org/2000/svg}image'):
        w = float(r.attrib['width']) * scale
        h = float(r.attrib['height']) * scale

        halfw = w / 2
        halfh = h / 2

        x = float(r.attrib['x']) * scale + halfw
        y = (height - float(r.attrib['y'])) * scale - halfh

        href = r.attrib['{http://www.w3.org/1999/xlink}href']
        if 'butterfly.png' in href:
            Butterfly(x, y)
        elif 'fly.png' in href:
            Fly(x, y)
        elif 'goldfish.png' in href:
            Goldfish(x, y)
        elif 'fish.png' in href:
            Fish(x, y)
        elif 'jumper.png' in href:
            level.pc = Frog(x, y)
        elif 'platform.png' in href:
            level.objs.append(
                Platform(x - halfw, y - halfh)
            )
