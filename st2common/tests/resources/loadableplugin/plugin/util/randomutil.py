import random


def get_random_numbers(count):
    return [random.randrange(0, 1000) for idx in xrange(0, count)]
