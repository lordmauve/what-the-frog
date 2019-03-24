import pyglet
import pyglet.sprite
import pyglet.resource

pyglet.resource.path = [
    'assets/',
]
pyglet.resource.reindex()


window = pyglet.window.Window(800, 600)




pc = pyglet.sprite.Sprite(
    pyglet.resource.image('sprites/jumper.png')
)



@window.event
def on_draw():
    window.clear()
    pc.draw()




pyglet.app.run()

