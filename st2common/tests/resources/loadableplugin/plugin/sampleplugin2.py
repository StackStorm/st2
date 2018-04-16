from __future__ import absolute_import
import plugin.util.randomutil


class SamplePlugin(object):
    def __init__(self):
        self.__count = 10

    def do_work(self):
        return plugin.util.randomutil.get_random_numbers(self.__count)
