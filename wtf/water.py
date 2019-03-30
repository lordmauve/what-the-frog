from math import copysign

import numpy as np
import moderngl

from .physics import space, box, BUOYANCY, WATER_DRAG, COLLISION_TYPE_WATER
from .state import UnderwaterState
from . import sounds


class WaterBatch:
    def __init__(self, mgl):
        self.mgl = mgl
        self.water_verts = mgl.buffer(reserve=8, dynamic=True)
        self.water_shader = mgl.program(
            vertex_shader='''
                #version 130

                in vec2 vert;
                in float depth;

                uniform mat4 mvp;
                varying vec2 uv;
                varying vec2 refl_uv;
                varying float vdepth;

                vec2 uv_pos(vec4 position) {
                    return (position.xy + vec2(1, 1)) * 0.5;
                }

                void main() {
                    gl_Position = mvp * vec4(vert, 0.0, 1.0);
                    uv = uv_pos(gl_Position);

                    vdepth = depth;
                    vec4 refl_pos = vec4(vert.x, vert.y + 2 * depth, 0, 1.0);
                    refl_uv = uv_pos(mvp * refl_pos);
                }
            ''',
            fragment_shader='''
                #version 130

                varying vec2 uv;
                varying vec2 refl_uv;
                varying float vdepth;
                uniform float t;
                uniform sampler2D diffuse;
                out vec3 f_color;

                void main() {
                    float offx = 2 * cos(uv.y + 0.2 * t) +
                                sin(3 * sin(60.0 * uv.x) + 0.5 * t);
                    float offy = 2 * cos(uv.x + 107 + 0.3 * t) + sin(
                        sin(60.0 * uv.y + 1.23 + 0.6 * t)
                        + (0.5 + 0.5 * sin(uv.x * 30 + t))
                        + 0.3 * t
                    );
                    vec2 offset_uv = uv + 0.005 * vec2(offx, offy);
                    offset_uv = vec2(
                        clamp(offset_uv.x, 0, 1),
                        clamp(offset_uv.y, 0, 1)
                    );
                    vec3 diff = texture(diffuse, offset_uv).rgb;
                    float refl_amount = 0.6 / (pow(vdepth * 2, 2) + 1);

                    vec3 refl_diff = texture(diffuse, refl_uv).rgb;

                    f_color = diff * 0.55 + vec3(0.1, 0.15, 0.2)
                              + refl_diff * refl_amount;
                }
            ''',
        )
        self.water_vao = mgl.simple_vertex_array(
            self.water_shader,
            self.water_verts,
            'vert',
            'depth',
        )
        self.t = 0
        self.mvp_uniform = self.water_shader.get('mvp', None)
        self.t_uniform = self.water_shader.get('t', None)

    def render(self, dt, mvp):
        if not Water.insts:
            return
        self.t += dt
        all_water = np.concatenate([w.vertices for w in Water.insts])
        depths = np.stack([
            np.zeros(len(all_water) // 2),
            all_water[::2, 1] - all_water[1::2, 1]
        ], axis=1).reshape((-1, 1))
        all_water = np.concatenate([all_water, depths], axis=1)
        all_water = all_water.reshape(-1).astype('f4').tobytes()

        if self.water_verts.size != len(all_water):
            self.water_verts = self.mgl.buffer(all_water, dynamic=True)
            self.water_vao = self.mgl.simple_vertex_array(
                self.water_shader,
                self.water_verts,
                'vert',
                'depth',
            )
        else:
            self.water_verts.write(all_water)

        self.mvp_uniform.write(mvp.tobytes())
        self.t_uniform.value = self.t
        self.water_vao.render(moderngl.TRIANGLE_STRIP)


class Water:
    """A rectangular body of water.

    Each water body has a ripple system that creates waves that move along
    the surface. Water bodies are rendered with refraction and reflection.

    """
    VCONV = np.array([0.05, 0.3, -0.8, 0.3, 0.05])
    LCONV = np.array([0.05, 0.9, 0.05])

    SUBDIV = 5

    insts = []

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
        self.insts.append(self)

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

    def delete(self):
        space.remove(self.shape)
        self.insts.remove(self)

    def pre_solve(arbiter, space, data):
        dt = space.current_time_step
        water, actor = arbiter.shapes
        body = actor.body
        if not body:
            return False

        inst = water.water

        bb = actor.cache_bb()

        a = round((bb.left - inst.x1) * inst.SUBDIV)
        b = round((bb.right - inst.x1) * inst.SUBDIV)
        a = max(0, a)
        b = min(b, len(inst.levels))

        levels = inst.levels[a:b] + inst.y
        frac_immersed = float(np.mean(np.clip(
            (levels - bb.bottom) / (bb.top - bb.bottom),
            0, 1
        )))
        if frac_immersed < 1:
            f = 0.6 ** dt
            vy = body.velocity.y
            vy = copysign(min(100, abs(vy)), vy)
            inst.velocities[a:b] = (
                inst.velocities[a:b] * f +
                vy * abs(vy) * 40 * (1.0 - f) / (b - a) * dt
            )
            body.underwater = UnderwaterState.SURFACE
        else:
            body.underwater = UnderwaterState.UNDERWATER

        buoyancy = getattr(body, 'buoyancy', None) or BUOYANCY * bb.area()
        drag = -body.velocity * WATER_DRAG

        # Both buoyancy and drag are scaled by how immersed we are
        force = (buoyancy + drag) * frac_immersed
        body.apply_force_at_local_point(force, body.center_of_gravity)
        return False

    def separate(arbiter, space, data):
        water, actor = arbiter.shapes
        body = actor.body
        if not body:
            return False
        body.underwater = UnderwaterState.DRY

    def begin(arbiter, space, data):
        water, other = arbiter.shapes
        if other.body:
            speed = other.body.velocity.length
            if speed > 20:
                sounds.play('splash1')
            elif speed > 10:
                sounds.play('splash1', volume=(speed - 10) / 10)
        return True

    handler = space.add_wildcard_collision_handler(COLLISION_TYPE_WATER)
    handler.begin = begin
    handler.pre_solve = pre_solve
    handler.separate = separate
