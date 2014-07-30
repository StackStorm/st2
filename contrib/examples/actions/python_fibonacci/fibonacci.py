#!/usr/bin/env python

import sys
import traceback


def fib(n):
    if n < 2:
        return n
    return fib(n - 2) + fib(n - 1)

if __name__ == '__main__':
    try:
        startNumber = int(sys.argv[1])
        endNumber = int(sys.argv[2])
        print map(fib, range(startNumber, endNumber))
        sys.exit(0)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.exit(e.message)
