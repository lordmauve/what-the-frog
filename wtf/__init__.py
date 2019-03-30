import sys
import pyglet.resource
import pathlib

root = pathlib.Path(__file__).parent.parent
sys.path.append(str(root / 'vendor/earcut-python'))

# Init asset paths here so that all submodules/subpackages can load assets
ASSETS_PATH = root / 'assets'
pyglet.resource.path = [str(ASSETS_PATH)]
pyglet.resource.reindex()


PIXEL_SCALE = 0.5  # Scale down for non-hidpi screens

# File where progress is saved
SAVE_PATH = root / '.save.json'
