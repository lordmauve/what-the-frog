import pyglet.resource

# Init asset paths here so that all submodules/subpackages can load assets
pyglet.resource.path = ['assets/']
pyglet.resource.reindex()
