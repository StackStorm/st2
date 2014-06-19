import logging
from triggerdispatcher import TriggerDispatcher


class ContainerService(object):
    __dispatcher = None
    __base_logger_name = 'st2reactor.sensorcontainer.sensors.'

    def __init__(self):
        self.__dispatcher = TriggerDispatcher()

    def get_dispatcher(self):
        return self.__dispatcher

    def dispatch(self, triggers):
        '''
        Pass through implementation.
        '''
        self.__dispatcher.dispatch(triggers)

    def get_logger(self, name):
        logger = logging.getLogger(self.__base_logger_name + name)
        logger.propagate = True
        return logger
