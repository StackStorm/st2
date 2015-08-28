#!/usr/bin/env python

from __future__ import print_function
import sys
import traceback

from six.moves import map


def fib(n):
    if n < 2:
        return n
    return fib(n - 2) + fib(n - 1)

if __name__ == '__main__':
    try:
        startNumber = int(float(sys.argv[1]))
        endNumber = int(float(sys.argv[2]))
        results = map(str, map(fib, list(range(startNumber, endNumber))))
        results = ' '.join(results)
        print(results)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.exit(e.message)
