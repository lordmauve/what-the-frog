import numpy as np
from pyglet import gl
import pyglet.graphics
from earcut.earcut import earcut
from pymunk import Poly

from .geom import SPACE_SCALE
from .physics import space


class RockPoly:
    batch = pyglet.graphics.Batch()
    TEX = pyglet.resource.texture('textures/rock.jpg')
    group = pyglet.sprite.SpriteGroup(
        TEX,
        gl.GL_SRC_ALPHA,
        gl.GL_ONE_MINUS_SRC_ALPHA,
    )

    def __init__(self, verts):
        self.indexes = earcut(verts)
        self.dl = self.batch.add_indexed(
            len(verts) // 2,
            gl.GL_TRIANGLES,
            self.group,
            self.indexes,
            ('v2f/static', np.array(verts) / SPACE_SCALE),
            ('t2f/static', np.array(verts) * 0.1)
        )

        self.shapes = []
        verts = np.array(verts)
        tris = verts.reshape(-1, 2)[self.indexes].reshape(-1, 3, 2)
        for tri in tris:
            shp = Poly(space.static_body, tri)
            space.add(shp)
            self.shapes.append(shp)

    def delete(self):
        self.dl.delete()
        space.remove(*self.shapes)
