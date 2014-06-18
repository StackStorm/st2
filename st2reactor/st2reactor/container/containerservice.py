from triggerdispatcher import TriggerDispatcher


class ContainerService(object):
    __dispatcher = None

    def __init__(self):
        self.__dispatcher = TriggerDispatcher()

    def get_dispatcher(self):
        return self.__dispatcher

    def dispatch(self, triggers):
        '''
        Pass through implementation.
        '''
        self.__dispatcher.dispatch(triggers)

