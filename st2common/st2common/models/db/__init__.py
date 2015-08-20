import copy
import importlib

import six
import mongoengine

from st2common.util import isotime
from st2common.models.db import stormbase
from st2common import log as logging


LOG = logging.getLogger(__name__)

MODEL_MODULE_NAMES = [
    'st2common.models.db.auth',
    'st2common.models.db.action',
    'st2common.models.db.actionalias',
    'st2common.models.db.keyvalue',
    'st2common.models.db.execution',
    'st2common.models.db.executionstate',
    'st2common.models.db.liveaction',
    'st2common.models.db.policy',
    'st2common.models.db.rule',
    'st2common.models.db.runner',
    'st2common.models.db.sensor',
    'st2common.models.db.trigger',
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


class MongoDBAccess(object):
    """Database object access class that provides general functions for a model type."""

    def __init__(self, model):
        self.model = model

    def get_by_name(self, value):
        return self.get(name=value, raise_exception=True)

    def get_by_id(self, value):
        return self.get(id=value, raise_exception=True)

    def get_by_ref(self, value):
        return self.get(ref=value, raise_exception=True)

    def get(self, exclude_fields=None, *args, **kwargs):
        raise_exception = kwargs.pop('raise_exception', False)

        instances = self.model.objects(**kwargs)

        if exclude_fields:
            instances = instances.exclude(*exclude_fields)

        instance = instances[0] if instances else None

        if not instance and raise_exception:
            raise ValueError('Unable to find the %s instance. %s' % (self.model.__name__, kwargs))
        return instance

    def get_all(self, *args, **kwargs):
        return self.query(*args, **kwargs)

    def count(self, *args, **kwargs):
        return self.model.objects(**kwargs).count()

    def query(self, offset=0, limit=None, order_by=None, exclude_fields=None,
              **filters):
        order_by = order_by or []
        exclude_fields = exclude_fields or []
        eop = offset + int(limit) if limit else None

        # Process the filters
        # Note: Both of those functions manipulate "filters" variable so the order in which they
        # are called matters
        filters, order_by = self._process_datetime_range_filters(filters=filters, order_by=order_by)
        filters = self._process_null_filters(filters=filters)

        result = self.model.objects(**filters)

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

    def _process_null_filters(self, filters):
        result = copy.deepcopy(filters)

        null_filters = {k: v for k, v in six.iteritems(filters)
                        if v is None or (type(v) in [str, unicode] and str(v.lower()) == 'null')}

        for key in null_filters.keys():
            result['%s__exists' % (key)] = False
            del result[key]

        return result

    def _process_datetime_range_filters(self, filters, order_by=None):
        ranges = {k: v for k, v in filters.iteritems()
                  if type(v) in [str, unicode] and '..' in v}

        order_by_list = copy.deepcopy(order_by) if order_by else []
        for k, v in ranges.iteritems():
            values = v.split('..')
            dt1 = isotime.parse(values[0])
            dt2 = isotime.parse(values[1])

            k__gte = '%s__gte' % k
            k__lte = '%s__lte' % k
            if dt1 < dt2:
                query = {k__gte: dt1, k__lte: dt2}
                sort_key, reverse_sort_key = k, '-' + k
            else:
                query = {k__gte: dt2, k__lte: dt1}
                sort_key, reverse_sort_key = '-' + k, k
            del filters[k]
            filters.update(query)

            if reverse_sort_key in order_by_list:
                idx = order_by_list.index(reverse_sort_key)
                order_by_list.pop(idx)
                order_by_list.insert(idx, sort_key)
            elif sort_key not in order_by_list:
                order_by_list = [sort_key] + order_by_list

        return filters, order_by_list
