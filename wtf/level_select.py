from pymunk import Vec2d
import pyglet.graphics
import pyglet.sprite
import pyglet.clock

from .directions import Direction
from . import ASSETS_PATH
from .sprites import load_centered
from .actors import actor_sprites
from .level_loader import NoSuchLevel
from .keys import KeyInputHandler
from . import sounds


START_LEVEL = "easy1"
LEVEL_SETS = [
    "easy",
    "level",
    "hard",
]


class LevelList:
    def __init__(self):
        self.levels = []
        for s in LEVEL_SETS:
            for f in ASSETS_PATH.glob(f'levels/{s}*.svg'):
                self.levels.append(f.stem)
        self.levels.sort(key=self.level_order)

    def __len__(self):
        return len(self.levels)

    def __getitem__(self, idx):
        return self.levels[idx]

    def level_order(self, name):
        stem = name.rstrip('0123456789')
        digit = int(name[len(stem):])
        group = LEVEL_SETS.index(stem)
        return group, digit

    def next(self, current):
        idx = self.levels.index[current]
        try:
            return self.levels[idx + 1]
        except KeyError:
            raise NoSuchLevel("You have won") from None


LEVELS = LevelList()


class HopTween:
    def __init__(self, sprite, duration=0.2):
        self.sprite = sprite
        self.duration = duration

    def go(self, target_pos):
        self.start_pos = Vec2d(*self.sprite.position)
        self.target_pos = Vec2d(*target_pos)

        self.t = 0
        pyglet.clock.schedule_once(self.update, 1 / 60)

    def update(self, dt):
        if not self.sprite:
            return
        self.t += dt
        if self.t > self.duration:
            self.sprite.position = self.target_pos
            return

        frac = self.t / self.duration

        position = self.start_pos + frac * (self.target_pos - self.start_pos)
        scale = 1.0 + frac * (1.0 - frac) * 4
        self.sprite.update(
            *position,
            scale=scale
        )
        pyglet.clock.schedule_once(self.update, 1 / 60)

    def stop(self):
        self.sprite = None
        pyglet.clock.unschedule(self.update)


class LevelSelectScreen:
    basegroup = pyglet.graphics.OrderedGroup(0)
    cursorgroup = pyglet.graphics.OrderedGroup(1)

    def __init__(self, window, slowmo=False):
        self.slowmo = slowmo
        self.window = window

        self.sprites = [
            pyglet.sprite.Sprite(
                load_centered('level-select', 'ui'),
                x=300,
                y=window.height - 80,
                batch=actor_sprites,
                group=self.basegroup,
            ),
            pyglet.sprite.Sprite(
                load_centered('lilypad', 'ui'),
                *self.screen_pos(0),
                batch=actor_sprites,
                group=self.basegroup,
            ),
        ]
        self.frog = pyglet.sprite.Sprite(
            load_centered('frog', 'ui'),
            *self.screen_pos(0),
            batch=actor_sprites,
            group=self.cursorgroup,
        )
        self.sprites.append(self.frog)
        self.tween = HopTween(self.frog)

        for i, level in enumerate(LEVELS, start=1):
            s = pyglet.sprite.Sprite(
                load_centered(level, 'levelthumbs'),
                *self.screen_pos(i),
                batch=actor_sprites,
                group=self.basegroup,
            )
            s.scale = 2
            self.sprites.append(s)

        self.cursor = 0

    def jump(self, direction):
        newcursor = self.cursor
        group, i = divmod(self.cursor, 5)
        col, row = divmod(i, 3)
        minrow = 0
        if col == 1:
            minrow = 1
            row += 1
        col += group * 2
        even = col % 2 == 0
        if direction is Direction.D:
            if row < 2:
                newcursor += 1
        elif direction is Direction.U:
            if row > minrow:
                newcursor -= 1
        elif direction is Direction.UR:
            if even:
                if row > 0:
                    newcursor += 2
            else:
                newcursor += 2
        elif direction is Direction.DR:
            if even:
                if row < 2:
                    newcursor += 3
            else:
                newcursor += 3
        elif direction is Direction.DL:
            if even:
                if row < 2:
                    newcursor -= 2
            else:
                newcursor -= 2
        elif direction is Direction.UL:
            if even:
                if row > 0:
                    newcursor -= 3
            else:
                newcursor -= 3

        if newcursor != self.cursor and 0 <= newcursor < len(LEVELS):
            self.cursor = newcursor
            self.tween.go(self.screen_pos(self.cursor))
            sounds.play('ribbit')

    def screen_pos(self, i):
        """Screen pos for the level at index i."""
        top = self.window.height - 320
        left = 200
        yspacing = 350
        xspacing = yspacing * 3 ** 0.5 / 2

        group, i = divmod(i, 5)
        col, row = divmod(i, 3)
        if col == 1:
            row += 1
        x = left + xspacing * (col + 2 * group)
        y = top - yspacing * (row - 0.5 * (col % 2))
        return x, y

    def start(self):
        try:
            self.window.pop_handlers()
        except Exception:
            pass
        self.window.push_handlers(self)
        self.window.push_handlers(KeyInputHandler(self.jump, self.window))
        from .main import hud
        hud.clear_card()
        hud.card = True  # hide the arrows

    def on_key_press(self, symbol, modifiers):
        if symbol in (pyglet.window.key.ENTER, pyglet.window.key.SPACE):
            if self.cursor != 0:
                self.start_selected()
        elif symbol == pyglet.window.key.ESCAPE:
            from .main import TitleScreen
            self.window.pop_handlers()
            TitleScreen().start()

    def start_selected(self):
        from .main import level, set_keyhandler, hud
        for s in self.sprites:
            s.delete()
        self.window.pop_handlers()
        self.window.pop_handlers()
        self.tween.stop()

        set_keyhandler(self.slowmo)
        hud.card = None
        level.load(LEVELS[self.cursor])
