import pyglet.resource
import pyglet.graphics
import pyglet.sprite

from .directions import Direction
from .sprites import load_centered

# Distance that the jump markers are inset from the edge
INSET = 40

RED = 255, 60, 60
GREEN = 103, 120, 33


def tween(v, target, dt):
    """Tween v back to target with an ease-out tween."""
    return target + (v - target) * 0.05 ** dt


class HUD:
    """The HUD, showing what jumps are available."""
    arrow = load_centered('arrow')

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.card = None

        self.batch = pyglet.graphics.Batch()
        self.available = dict.fromkeys(Direction, True)
        self.arrows = {}
        for d in Direction:
            s = pyglet.sprite.Sprite(
                self.arrow,
                batch=self.batch
            )
            if 'U' in d.name:
                s.y = height - INSET
            elif 'D' in d.name:
                s.y = INSET
            else:
                s.y = height // 2
            if 'L' in d.name:
                s.x = INSET
            elif 'R' in d.name:
                s.x = width - INSET
            else:
                s.x = width // 2
            s.rotation = -d.value.angle_degrees
            s.color = GREEN
            s.opacity = 180
            self.arrows[d] = s

    def show_card(self, name):
        """Show a card."""
        self.card = pyglet.sprite.Sprite(
            load_centered(name, 'cards'),
            batch=self.batch
        )
        self.card.position = (
            self.width // 2,
            self.height // 2
        )

    def clear_card(self):
        if self.card:
            self.card.delete()
            self.card = None

    def set_available(self, dir, available):
        """Set the availability of the direction."""
        self.clear_card()  # hack
        self.available[dir] = available
        s = self.arrows[dir]
        if available:
            s.color = GREEN
            s.opacity = 180
        s.scale = 3

    def warn_unavailable(self, dir):
        """Play an animation indicating that the direction is unavailable."""
        s = self.arrows[dir]
        s.color = RED
        s.opacity = 180
        s.scale = 3

    def update(self, dt):
        if self.card:
            for v in self.arrows.values():
                v.opacity = 0
            return
        for d, s in self.arrows.items():
            s.scale = tween(s.scale, 1, dt)
            if not self.available[d]:
                s.opacity = tween(s.opacity, 0, dt)
                s.color = tuple(
                    tween(c, t, dt) for c, t in zip(s.color, RED)
                )
            else:
                s.opacity = 180

    def draw(self):
        """Draw the HUD."""
        self.batch.draw()
