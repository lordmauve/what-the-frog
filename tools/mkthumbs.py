from pathlib import Path
import subprocess

cwd = Path.cwd()


for f in cwd.glob('assets/levelpics/*.png'):
    dest = cwd / 'assets' / 'levelthumbs' / f'{f.stem}.jpg'
    subprocess.check_call(
        ['convert', '-resize', '120x', f, dest]
    )
