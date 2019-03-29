import argparse
import random

dirs = ['UL', 'U', 'UR', 'DL', 'D', 'DR', '*']


def gen(n=6):
    moves = []
    avail = dirs[:]
    for x in range(n):
        m = random.choice(avail)
        avail.remove(m)
        moves.append(m)
        if m == '*':
            avail[:] = dirs
    return moves


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=int, default=6)
    args = parser.parse_args()
    print(*gen(args.steps))


if __name__ == '__main__':
    main()
