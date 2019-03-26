import numpy as np
import re
import pyglet.resource
from xml.etree.ElementTree import parse
from pymunk import Vec2d

from .water import Water
from .geom import SPACE_SCALE
from .poly import RockPoly


COMMA_WSP = re.compile(r'(?:\s+,?\s*|,\s*)')


def path_toks(path):
    """Iterate over components of path as tokens."""
    toks = COMMA_WSP.split(path)
    for tok in toks:
        if tok.isalpha():
            yield tok
        else:
            v = float(tok)
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


def load_level(level):
    f = pyglet.resource.file(f'levels/{level.name}.svg')
    doc = parse(f)
    height = float(doc.getroot().attrib['height'])
    for path in doc.findall('.//{http://www.w3.org/2000/svg}path'):
        for loop in parse_path(path.attrib['d']):
            verts = np.array(
                [(2 * x, 2 * (height - y)) for x, y in loop],
            )
            level.objs.append(
                RockPoly(
                    verts.reshape(-1) * SPACE_SCALE,
                    draw=False
                )
            )

    for r in doc.findall('.//{http://www.w3.org/2000/svg}rect'):
        x1 = float(r.attrib['x']) * 2 * SPACE_SCALE
        y = (height - float(r.attrib['y'])) * 2 * SPACE_SCALE
        x2 = x1 + float(r.attrib['width']) * 2 * SPACE_SCALE
        y_bot = y - float(r.attrib['height']) * 2 * SPACE_SCALE
        assert y > y_bot
        Water(y, round(x1), round(x2), y_bot)
