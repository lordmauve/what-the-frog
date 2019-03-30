import datetime
import pathlib
from itertools import count

from pyglet import gl
import pyglet.image


def screenshot_path(comp_start=datetime.date(2019, 3, 24)):
    """Get a path to save a screenshot into."""
    today = datetime.date.today()
    comp_day = (today - comp_start).days + 1
    grabs = pathlib.Path('grabs')

    for n in count(1):
        p = grabs / f'day{comp_day}-{n}.png'
        if not p.exists():
            return str(p)


def take_screenshot(window, path=None):
    """Take a screenshot of the given window.

    Save it to a new path returned by screenshot_path.

    """
    # disable transfer alpha channel
    gl.glPixelTransferf(gl.GL_ALPHA_BIAS, 1.0)
    image = pyglet.image.ColorBufferImage(
        0,
        0,
        window.width,
        window.height
    )
    image.save(path or screenshot_path())
    # re-enable alpha channel transfer
    gl.glPixelTransferf(gl.GL_ALPHA_BIAS, 0.0)
