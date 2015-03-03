import importlib

import mongoengine

from st2common.util import isotime
from st2common.models.db import stormbase
from st2common import log as logging


LOG = logging.getLogger(__name__)

MODEL_MODULE_NAMES = [
    'st2common.models.db.access',
    'st2common.models.db.action',
    'st2common.models.db.actionrunner',
    'st2common.models.db.datastore',
    'st2common.models.db.execution',
    'st2common.models.db.reactor'
]


def db_setup(db_name, db_host, db_port, username=None, password=None):
    LOG.info('Connecting to database "%s" @ "%s:%s" as user "%s".' %
             (db_name, db_host, db_port, str(username)))
    connection = mongoengine.connection.connect(db_name, host=db_host,
                                                port=db_port, tz_aware=True,
                                                username=username, password=password)

    # Create all the indexes upfront to prevent race-conditions caused by
    # lazy index creation
    db_ensure_indexes()

    return connection


def db_ensure_indexes():
    """
    This function ensures that indexes for all the models have been created.

    Note #1: When calling this method database connection already needs to be
    established.

    Note #2: This method blocks until all the index have been created (indexes
    are created in real-time and not in background).
    """
    LOG.debug('Ensuring database indexes...')

    for module_name in MODEL_MODULE_NAMES:
        module = importlib.import_module(module_name)
        model_classes = getattr(module, 'MODELS', [])
        for cls in model_classes:
            LOG.debug('Ensuring indexes for model "%s"...' % (cls.__name__))
            cls.ensure_indexes()


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
        ranges = {k: v for k, v in kwargs.iteritems()
                  if type(v) in [str, unicode] and '..' in v}
        for k, v in ranges.iteritems():
            values = v.split('..')
            dt1 = isotime.parse(values[0])
            dt2 = isotime.parse(values[1])
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
        # TODO: Fix kwargs abuse
        offset = int(kwargs.pop('offset', 0))
        limit = kwargs.pop('limit', None)
        order_by = kwargs.pop('order_by', [])
        exclude_fields = kwargs.pop('exclude_fields', [])
        eop = offset + int(limit) if limit else None

        result = self.model.objects(**kwargs)

        if exclude_fields:
            result = result.exclude(*exclude_fields)

        result = result.order_by(*order_by)
        result = result[offset:eop]

        return result

    def distinct(self, *args, **kwargs):
        field = kwargs.pop('field')
        return self.model.objects(**kwargs).distinct(field)

    def aggregate(self, *args, **kwargs):
        return self.model.objects(**kwargs)._collection.aggregate(*args, **kwargs)

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
