from contextlib import contextmanager

import moderngl
import numpy as np


verts = np.array([
    (-1, -1),
    (+1, -1),
    (-1, +1),
    (+1, +1),
])
texcoords = np.array([
    (0, 0),
    (1, 0),
    (1, 1),
    (0, 1)
])


class OffscreenBuffer:
    def __init__(self, width, height, mgl):
        size = self.size = width, height
        self.mgl = mgl

        self.fbuf = mgl.framebuffer(
            [mgl.texture(size, components=3)],
            mgl.depth_renderbuffer(size)
        )

        self.shader = mgl.program(
            vertex_shader='''
                #version 130

                in vec2 vert;

                varying vec2 uv;

                void main() {
                    gl_Position = vec4(vert, 0.0, 1.0);
                    uv = (vert + vec2(1, 1)) * 0.5;
                }
            ''',
            fragment_shader='''
                #version 130

                varying vec2 uv;
                uniform sampler2D diffuse;
                out vec3 f_color;

                void main() {
                    f_color = texture(diffuse, uv).rgb;
                    //f_color = vec3(uv, 0);
                }
            ''',
        )

        self.quad = mgl.buffer(verts.astype('f4').tobytes())
        self.vao = mgl.simple_vertex_array(
            self.shader,
            self.quad,
            'vert',
        )

    def draw(self):
        with self.bind_texture():
            self.vao.render(moderngl.TRIANGLE_STRIP)

    @contextmanager
    def bind_texture(self, location=0):
        self.fbuf.color_attachments[0].use(location=location)
        yield

    @contextmanager
    def bind_buffer(self):
        """Bind the framebuffer for rendering."""
        self.fbuf.use()
        try:
            yield self.fbuf
        finally:
            self.mgl.screen.use()
