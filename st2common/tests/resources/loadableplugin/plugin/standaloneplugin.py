class SamplePlugin(object):
    def __init__(self):
        self.__count = 10

    def do_work(self):
        return self.__count


class FooPlugin(object):
    """
    Some class that doesn't implement the specified plugin interface.
    """

    def foo():
        pass
