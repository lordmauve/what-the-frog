import numpy as np

from .physics import space, box, BUOYANCY, WATER_DRAG, COLLISION_TYPE_WATER


class Water:
    """A rectangular body of water.

    Each water body has a ripple system that creates waves that move along
    the surface. Water bodies are rendered with refraction and reflection.

    """
    VCONV = np.array([0.05, 0.3, -0.8, 0.3, 0.05])
    LCONV = np.array([0.05, 0.9, 0.05])

    SUBDIV = 5

    def __init__(self, surf_y, x1, x2, bot_y=0):
        self.y = surf_y
        self.x1 = x1
        self.x2 = x2

        self.shape = box(
            space.static_body,
            x=x1,
            y=bot_y,
            w=x2 - x1,
            h=surf_y - bot_y
        )
        self.shape.water = self
        self.shape.collision_type = COLLISION_TYPE_WATER
        space.add(self.shape)

        size = int(x2 - x1) * self.SUBDIV + 1
        self.xs = np.linspace(x1, x2, size)
        self.velocities = np.zeros(size)
        self.levels = np.zeros(size)
        self.bot_verts = np.ones(size) * bot_y

    def update(self, dt):
        self.velocities += np.convolve(
            self.levels,
            self.VCONV * (dt * 60),
            'same',
        )
        self.velocities *= 0.5 ** dt  # damp
        self.levels = np.convolve(
            self.levels,
            self.LCONV,
            'same'
        ) + self.velocities * 10 * dt  # apply velocity

        verts = np.dstack((
            self.xs,
            self.levels + self.y,
            self.xs,
            self.bot_verts,
        ))
        self.vertices = verts.reshape((-1, 2))

    def drip(self, _):
        self.levels[-9] = -0.5
        self.velocities[-9] = 0

    @classmethod
    def draw(cls):
        cls.water_batch.draw()

    def pre_solve(arbiter, space, data):
        dt = space.current_time_step
        water, actor = arbiter.shapes
        body = actor.body
        if not body:
            return False

        inst = water.water

        bb = actor.cache_bb()

        a = round(bb.left - inst.x1) * inst.SUBDIV
        b = round(bb.right - inst.x1) * inst.SUBDIV
        levels = inst.levels[a:b] + inst.y
        frac_immersed = float(np.mean(np.clip(
            (levels - bb.bottom) / (bb.top - bb.bottom),
            0, 1
        )))
        if frac_immersed < 1:
            f = 0.6 ** dt
            inst.velocities[a:b] = (
                inst.velocities[a:b] * f +
                body.velocity.y * abs(body.velocity.y) * 0.1 * (1.0 - f)
            )

        buoyancy = BUOYANCY * bb.area()
        drag = -body.velocity * WATER_DRAG

        # Both buoyancy and drag are scaled by how immersed we are
        force = (buoyancy + drag) * frac_immersed
        body.apply_force_at_local_point(force, body.center_of_gravity)
        return False

    handler = space.add_wildcard_collision_handler(COLLISION_TYPE_WATER)
    handler.pre_solve = pre_solve
