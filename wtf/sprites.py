import pyglet.resource


def load_centered(name, group='sprites'):
    img = pyglet.resource.image(f'{group}/{name}.png')
    img.anchor_x = img.width // 2
    img.anchor_y = img.height // 2
    return img


def center(obj):
    if isinstance(obj, pyglet.image.AbstractImageSequence):
        seq = obj.get_texture_sequence()
        for img in seq.items:
            img.anchor_x = img.width // 2
            img.anchor_y = img.height // 2
        return seq
    else:
        obj.anchor_x = obj.width // 2
        obj.anchor_y = obj.height // 2
        return obj
