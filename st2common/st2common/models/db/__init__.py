import logging
from mongoengine.connection import connect, disconnect
from oslo.config import cfg

LOG = logging.getLogger('st2common.models.db')


def db_setup(db_name, db_host, db_port):
    LOG.info('Database details - dbname:{}, host:{}, port:{}'.format(
        db_name, db_host, db_port))
    connect(db_name, host=db_host, port=db_port)


def db_teardown():
    disconnect()


class MongoDBAccess(object):
    """
    Db Object Access class. Provides general implementation which should be
    specialized for a model type.
    """
    def __init__(self, model_kls):
        self._model_kls = model_kls

    def get_by_name(self, value):
        for model_object in self._model_kls.objects(name=value):
            return model_object
        raise ValueError('{} with name "{}" does not exist.'.format(
            self._model_kls.__name__, value))

    def get_by_id(self, value):
        for model_object in self._model_kls.objects(id=value):
            return model_object
        raise ValueError('{} with id "{}" does not exist.'.format(
            self._model_kls.__name__, value))

    def get_all(self):
        return self._model_kls.objects()

    def query(self, **query_args):
        return self._model_kls.objects(**query_args)

    @staticmethod
    def add_or_update(model_object):
        return model_object.save()

    @staticmethod
    def delete(model_object):
        model_object.delete()
