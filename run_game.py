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


from wtf.main import run
run()

