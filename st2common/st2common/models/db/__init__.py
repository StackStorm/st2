import datetime

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


def process_datetime_ranges(func):
    def decorate(*args, **kwargs):
        pattern = '%Y%m%dT%H%M%S%f'
        ranges = {k: v for k, v in kwargs.iteritems()
                  if type(v) in [str, unicode] and '..' in v}
        for k, v in ranges.iteritems():
            values = v.split('..')
            dt1 = datetime.datetime.strptime(values[0].ljust(21, '0'), pattern)
            dt2 = datetime.datetime.strptime(values[1].ljust(21, '0'), pattern)
            order_by_list = kwargs.get('order_by', [])
            k__gte = '%s__gte' % k
            k__lte = '%s__lte' % k
            if dt1 < dt2:
                query = {k__gte: dt1, k__lte: dt2}
                sort_key, reverse_sort_key = k, '-' + k
            else:
                query = {k__gte: dt2, k__lte: dt1}
                sort_key, reverse_sort_key = '-' + k, k
            del kwargs[k]
            kwargs.update(query)
            if reverse_sort_key in order_by_list:
                idx = order_by_list.index(reverse_sort_key)
                order_by_list.pop(idx)
                order_by_list.insert(idx, sort_key)
            elif sort_key not in order_by_list:
                kwargs['order_by'] = [sort_key] + order_by_list
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
    @process_datetime_ranges
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
