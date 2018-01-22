#! /usr/bin/python

from __future__ import absolute_import

import argparse
import string

try:
    from string import letters as ascii_letters
except ImportError:
    from string import ascii_letters

import random


def print_random_chars(chars=1000, selection=ascii_letters + string.digits):
    s = []
    for _ in range(chars - 1):
        s.append(random.choice(selection))
    s.append('@')
    print(''.join(s))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chars', type=int, metavar='N', default=10)
    args = parser.parse_args()
    print_random_chars(args.chars)


if __name__ == '__main__':
    main()
