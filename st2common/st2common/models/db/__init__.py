from mongoengine.connection import connect, disconnect

from st2common.models.db import stormbase
from st2common.util import mongoescape as util
from st2common import log as logging


LOG = logging.getLogger('st2common.models.db')


def db_setup(db_name, db_host, db_port):
    LOG.info('Database details - dbname:{}, host:{}, port:{}'.format(
        db_name, db_host, db_port))
    return connect(db_name, host=db_host, port=db_port)


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

    def get_all(self, *args, **kwargs):
        order_by = kwargs.pop('order_by', ['name'])
        limit = kwargs.pop('limit', None)
        if limit and limit <= 0:
            limit = None
        return self.query(order_by, limit, **kwargs)

    def query(self, order_by=[], limit=None, **query_args):
        if not limit:
            return (self._model_kls.objects(**query_args).order_by(*order_by)
                    if order_by else self._model_kls.objects(**query_args))
        else:
            return (self._model_kls.objects(**query_args).order_by(*order_by)[:limit]
                    if order_by else self._model_kls.objects(**query_args)[:limit])

    @staticmethod
    def add_or_update(model_object):
        model_object.save()
        fields = {k: v for k, v in model_object._fields.iteritems()
                  if isinstance(v, stormbase.EscapedDictField)}
        for attr, field in fields.iteritems():
            value = util.unescape_chars(getattr(model_object, attr))
            setattr(model_object, attr, value)
        return model_object

    @staticmethod
    def delete(model_object):
        model_object.delete()
