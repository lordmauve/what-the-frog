# flake8: noqa
import sys

if sys.version_info < (3, 7):
    sys.exit(
        "This game requires Python 3.7 or later. "
        "(Just for a dataclass or two; should be a quick port to Python 3.6)."
    )


missing = set()
try:
    import pyglet
except ImportError:
    missing.add('pyglet')

try:
    import pymunkoptions
except ImportError:
    missing.add('PyMunk')

try:
    import numpy
except ImportError:
    missing.add('numpy')

try:
    import moderngl
except ImportError:
    missing.add('moderngl')

try:
    import pyrr
except ImportError:
    missing.add('pyrr')

if missing:
    sys.exit(
        "You are missing required dependencies: {deps}\n\n"
        "Please install the versions listed in requirements.txt.".format(
            deps=', '.join(sorted(missing))
        )
    )


if not __debug__:
    pymunkoptions.options["debug"] = __debug__
else:
    import pymunk  # noqa: F401: importing to trigger message
    print("Run with -O for best performance.")


def default_scale():
    """Estimate the pixel scale that will fit on this screen."""
    scale = 2.0
    w = 1600
    h = 1200
    platform = pyglet.window.get_platform()
    display = platform.get_default_display()
    screen = display.get_default_screen()
    avail_width = screen.width - 50
    avail_height = screen.height - 50
    while w > avail_width or h > avail_height:
        scale *= 0.5
        w *= 0.5
        h *= 0.5
    return scale


from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument(
    'levelname',
    nargs='?',
    help="The level to start on.",
    default=None
)
parser.add_argument(
    '--pixel-scale',
    type=float,
    default=default_scale(),
    help="The scaling to use. Defaults to a value that will fit your screen."
)

args = parser.parse_args()

import wtf
wtf.PIXEL_SCALE *= args.pixel_scale

import wtf.main
wtf.main.run(args.levelname)
