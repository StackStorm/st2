import mongoengine

from st2common.models.db import stormbase
from st2common import log as logging


LOG = logging.getLogger(__name__)


def db_setup(db_name, db_host, db_port):
    LOG.info('Connecting to database "%s" @ "%s:%s"' % (db_name, db_host, db_port))
    return mongoengine.connection.connect(db_name, host=db_host, port=db_port)


def db_teardown():
    mongoengine.connection.disconnect()


def process_null_filter(func):
    def decorate(*args, **kwargs):
        filters = {k: v for k, v in kwargs.iteritems()
                   if v is None or (type(v) in [str, unicode] and str(v.lower()) == 'null')}
        for k, v in filters.iteritems():
            kwargs['%s__exists' % k] = False
            del kwargs[k]
        return func(*args, **kwargs)
    return decorate


class MongoDBAccess(object):
    """Database object access class that provides general functions for a model type."""

    def __init__(self, model):
        self.model = model

    def get_by_name(self, value):
        return self.get(name=value, raise_exception=True)

    def get_by_id(self, value):
        return self.get(id=value, raise_exception=True)

    def get(self, *args, **kwargs):
        raise_exception = kwargs.pop('raise_exception', False)
        instances = self.model.objects(**kwargs)
        instance = instances[0] if instances else None
        if not instance and raise_exception:
            raise ValueError('Unable to find the %s instance. %s' % (self.model.__name__, kwargs))
        return instance

    def get_all(self, *args, **kwargs):
        return self.query(*args, **kwargs)

    def count(self, *args, **kwargs):
        return self.model.objects(**kwargs).count()

    @process_null_filter
    def query(self, *args, **kwargs):
        offset = int(kwargs.pop('offset', 0))
        limit = kwargs.pop('limit', None)
        eop = offset + int(limit) if limit else None
        order_by = kwargs.pop('order_by', [])
        return self.model.objects(**kwargs).order_by(*order_by)[offset:eop]

    @staticmethod
    def add_or_update(instance):
        instance.save()
        for attr, field in instance._fields.iteritems():
            if isinstance(field, stormbase.EscapedDictField):
                value = getattr(instance, attr)
                setattr(instance, attr, field.to_python(value))
        return instance

    @staticmethod
    def delete(instance):
        instance.delete()
