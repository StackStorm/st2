class SamplePlugin(object):
    def __init__(self):
        self.__count = 10

    def do_work(self):
        return self.__count


def get_plugin():
    return SamplePlugin()
