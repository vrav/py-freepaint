from math import sqrt
from ctypes import c_int

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL import GL
from OpenGL.GL import shaders

from modules.math import mat4_ortho, mat4_mul, mat4_identity, mat4_translate, mat4_rotate_z_at_point, mat4_scale_at_point, mat4_flip_horizontal_at_point
from modules.gl.gltypes import Program, RenderTarget, DualFramebuffer

DEFAULT_CANVAS = {
    "verts": [
        0, 0, 0,
        0, 1, 0,
        1, 0, 0,
        1, 1, 0,
    ],
    "uvs": [
        0, 0,
        0, 1,
        1, 0,
        1, 1,
    ]
}

DEFAULT_SCREENQUAD = {
    "verts": [
       -1,-1, 0,
       -1, 1, 0,
        1,-1, 0,
        1, 1, 0,
    ],
    "uvs": [
        0, 0,
        0, 1,
        1, 0,
        1, 1,
    ]
}

class Renderer:
    def __init__(self, window_size, canvas_size, input_state):
        self.window_size = window_size
        self.input_state = input_state

        self.ortho_matrix = mat4_ortho(self.window_size[0], self.window_size[1])

        GL.glEnable( GL.GL_MULTISAMPLE )
        GL.glClearColor(0, 0, 0, 1)

        self.system_framebuffer_id = GL.glGetIntegerv( GL.GL_FRAMEBUFFER_BINDING )

        self.canvas = DualFramebuffer(canvas_size, canvas_size, (0.5, 0.5, 0.5, 1.0), True)

        self.view = RenderTarget(
            {
                "vertex shader path": "shaders/canvas.vert",
                "fragment shader path": "shaders/canvas.frag",
            }, {
                "vertices": [v * canvas_size for v in DEFAULT_CANVAS["verts"]],
                "uvs": DEFAULT_CANVAS["uvs"],
            }, {
                "width": self.window_size[0],
                "height": self.window_size[0],
                "color": (0.4, 0.4, 0.4, 1),
                "generate mipmaps": False
            }
        )
        self.view_transform = mat4_identity()
        self.view_scale_amount = 1.0
        self.view_reset()

        self.screen = RenderTarget(
            {
                "vertex shader path": "shaders/screen.vert",
                "fragment shader path": "shaders/screen.frag",
            }, {
                "vertices": DEFAULT_SCREENQUAD["verts"],
                "uvs": DEFAULT_SCREENQUAD["uvs"],
            }, {
                "dummy": True,
                "width": self.window_size[0],
                "height": self.window_size[1],
                "color": (0.2, 0.2, 0.2, 1),
                "generate mipmaps": False
            }
        )
        self.screen.fb.id = self.system_framebuffer_id

    def view_reset(self):
        self.view_flipped = False
        self.view_transform = mat4_identity()
        hz = self.canvas.fbs[0].width * 0.5
        mat4_translate(self.view_transform, self.window_size[0] * 0.5 - hz, self.window_size[1] * 0.5 - hz, 0)
        self.view_scale_amount = 1.0

    def view_translate(self, x, y):
        mat4_translate(self.view_transform, x, y, 0)
    
    def view_rotate_at_point(self, x, y, a):
        mat4_rotate_z_at_point(self.view_transform, x, y, a)

    def view_scale_at_point(self, x, y, s):
        mat4_scale_at_point(self.view_transform, x, y, s)
        vt = self.view_transform
        self.view_scale_amount = sqrt(pow(vt[0][0], 2) + pow(vt[0][1], 2) + pow(vt[0][2], 2))
    
    def view_flip_at_point(self, x):
        self.view_flipped = False if self.view_flipped else True
        mat4_flip_horizontal_at_point(self.view_transform, x)

    def close(self):
        pass

    def resize_window(self, window_size):
        self.window_size = window_size
        GL.glBindTexture( GL.GL_TEXTURE_2D, self.view.fb.texture.id )
        GL.glTexImage2D( GL.GL_TEXTURE_2D, 0, GL.GL_RGB16, self.window_size[0], self.window_size[1], 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, None)
        self.ortho_matrix = mat4_ortho(self.window_size[0], self.window_size[1])
        self.screen.fb.width = window_size[0]
        self.screen.fb.height = window_size[1]
        self.view.fb.width = window_size[0]
        self.view.fb.height = window_size[1]
        self.view_reset()

    def render(self):
        self.view_transform_screen = mat4_mul(self.view_transform, self.ortho_matrix)
        
        self.view.render({
            "basetexture": self.canvas.fbs[0].texture if self.canvas.toggle else self.canvas.fbs[1].texture,
            "transform": self.view_transform_screen
        })

        self.screen.render({
            "brushcolor": self.input_state.brush.color,
            "opacity": self.input_state.brush.opacity,
            "diam": max(self.input_state.brush.size * self.view_scale_amount, 1.0),
            "mpos": (self.input_state.mpos[0] / self.window_size[0], self.input_state.mpos[1] / self.window_size[1]),
            "winsize": (self.window_size[0], self.window_size[1]),
            "basetexture": self.view.fb.texture,
            "showcolor": 1 if self.input_state.brush.showcolor else 0,
            "softness": self.input_state.brush.softness,
        })
