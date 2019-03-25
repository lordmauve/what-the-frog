import sys
import pyglet.resource
import pathlib

root = pathlib.Path(__file__).parent.parent
sys.path.append(str(root / 'vendor/earcut-python'))

# Init asset paths here so that all submodules/subpackages can load assets
pyglet.resource.path = ['assets/']
pyglet.resource.reindex()
