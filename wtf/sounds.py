"""Support for playing sounds.

We use Pygame for audio because Pyglet's audio has proven to be unstable
in many previous PyWeeks.
"""
import random
import pygame.mixer
import pyglet.resource
from functools import lru_cache

pygame.mixer.pre_init(44000, 16, 2)
pygame.mixer.init()


AMBIENT_FILE = "sounds/ambient.ogg"
JUMP_SOUND_VOLUME = 0.4


@lru_cache()
def load(name):
    """Load a sound with the given name.

    Memoized to avoid re-loading sounds.
    """
    with pyglet.resource.file(f'sounds/{name}.wav', 'rb') as f:
        return pygame.mixer.Sound(f)


def play(name, volume=1.0):
    """Play a sound file."""
    s = load(name)
    s.set_volume(volume)
    s.play()


JUMPS = [
    load('jump1'),
    load('jump2'),
    load('jump3'),
]
JUMPS_UW = [
    load('jump-uw1'),
    load('jump-uw2'),
]

for s in JUMPS + JUMPS_UW:
    s.set_volume(JUMP_SOUND_VOLUME)


def jump(underwater=False):
    """Play a random jump sound."""
    random.choice(JUMPS_UW if underwater else JUMPS).play()


music_file = pyglet.resource.file(AMBIENT_FILE, 'rb')
pygame.mixer.music.load(music_file)
pygame.mixer.music.play(loops=-1)
