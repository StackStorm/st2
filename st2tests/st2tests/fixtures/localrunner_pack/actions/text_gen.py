#! /usr/bin/python

import argparse
import string
import random


def print_random_chars(chars=1000, selection=string.letters + string.digits):
    s = []
    for _ in range(chars - 1):
        s.append(random.choice(selection))
    s.append('@')
    print(''.join(s))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chars', type=int, metavar='N')
    args = parser.parse_args()
    print_random_chars(args.chars)


if __name__ == '__main__':
    main()
