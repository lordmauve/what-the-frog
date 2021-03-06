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

    FRICTION = 1.0
    ELASTICITY = 0.6

    def __init__(self, verts, color=(1, 1, 1), draw=True, friction=None):
        self.indexes = earcut(verts)

        if draw:
            size = len(verts) // 2
            self.dl = self.batch.add_indexed(
                size,
                gl.GL_TRIANGLES,
                self.group,
                self.indexes,
                ('v2f/static', np.array(verts) / SPACE_SCALE),
                ('t2f/static', np.array(verts) / (512 * SPACE_SCALE * 2)),
                ('c3f/static', [c for _ in range(size) for c in color]),
            )
        else:
            self.dl = None

        self.shapes = []
        verts = np.array(verts)
        tris = verts.reshape(-1, 2)[self.indexes].reshape(-1, 3, 2)
        for tri in tris:
            shp = Poly(space.static_body, tri)
            shp.friction = friction or self.FRICTION
            shp.elasticity = self.ELASTICITY
            space.add(shp)
            self.shapes.append(shp)

    def delete(self):
        if self.dl:
            self.dl.delete()
        space.remove(*self.shapes)
