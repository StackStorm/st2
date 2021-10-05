# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import sys

# NOTE: We need to perform eventlet monkey patching, especially the thread module before importing
# pymongo and mongoengine. If we don't do that, tests will hang because pymongo connection checker
# thread will be constructed before monkey patching with reference to non patched threading module.
# This is not an issue for any service where we have code structured correctly so we perform
# monkey patching as early as possible, but this is not always the case with tests and when monkey
# patching happens inside the tests really depends on tests import ordering, etc.
#
# One option would be to simply add monkey_patch() call to the top of every single test file, but
# this would result in tons of duplication.
#
# Another option is to simply perform monkey patching right here before importing pymongo in case
# we detected we are running inside tests.
#
# And third option is to re-arrange the imports so we lazily import pymongo + mongoengine when we
# first need it because monkey patching will already be performed by then.
#
# For now, we go with option 2) since it seems to be good enough of a compromise. We detect if we
# are running inside tests by checking if "nose" module is present - the same logic we already use
# in a couple of other places (and something which would need to be changed if we switch to pytest).
if "nose" in sys.modules.keys():
    from st2common.util.monkey_patch import monkey_patch

    monkey_patch()

import copy
import importlib
import traceback
import ssl as ssl_lib

import six
from oslo_config import cfg
import mongoengine
from mongoengine.queryset import visitor
from pymongo import uri_parser
from pymongo.errors import OperationFailure
from pymongo.errors import ConnectionFailure
from pymongo.errors import ServerSelectionTimeoutError

from st2common import log as logging
from st2common.util import isotime
from st2common.util.misc import get_field_name_from_mongoengine_error
from st2common.models.db import stormbase
from st2common.models.utils.profiling import log_query_and_profile_data_for_queryset
from st2common.exceptions import db as db_exc


LOG = logging.getLogger(__name__)

MODEL_MODULE_NAMES = [
    "st2common.models.db.auth",
    "st2common.models.db.action",
    "st2common.models.db.actionalias",
    "st2common.models.db.keyvalue",
    "st2common.models.db.execution",
    "st2common.models.db.executionstate",
    "st2common.models.db.execution_queue",
    "st2common.models.db.liveaction",
    "st2common.models.db.notification",
    "st2common.models.db.pack",
    "st2common.models.db.policy",
    "st2common.models.db.rbac",
    "st2common.models.db.rule",
    "st2common.models.db.rule_enforcement",
    "st2common.models.db.runner",
    "st2common.models.db.sensor",
    "st2common.models.db.trace",
    "st2common.models.db.trigger",
    "st2common.models.db.webhook",
    "st2common.models.db.workflow",
]

# A list of model names for which we don't perform extra index cleanup
INDEX_CLEANUP_MODEL_NAMES_BLACKLIST = ["PermissionGrantDB"]

# Reference to DB model classes used for db_ensure_indexes
# NOTE: This variable is populated lazily inside get_model_classes()
MODEL_CLASSES = None


def get_model_classes():
    """
    Retrieve a list of all the defined model classes.

    :rtype: ``list``
    """
    global MODEL_CLASSES

    if MODEL_CLASSES:
        return MODEL_CLASSES

    result = []
    for module_name in MODEL_MODULE_NAMES:
        module = importlib.import_module(module_name)
        model_classes = getattr(module, "MODELS", [])
        result.extend(model_classes)

    MODEL_CLASSES = result
    return MODEL_CLASSES


def _db_connect(
    db_name,
    db_host,
    db_port,
    username=None,
    password=None,
    ssl=False,
    ssl_keyfile=None,
    ssl_certfile=None,
    ssl_cert_reqs=None,
    ssl_ca_certs=None,
    authentication_mechanism=None,
    ssl_match_hostname=True,
):

    if "://" in db_host:
        # Hostname is provided as a URI string. Make sure we don't log the password in case one is
        # included as part of the URI string.
        uri_dict = uri_parser.parse_uri(db_host)
        username_string = uri_dict.get("username", username) or username

        if uri_dict.get("username", None) and username:
            # Username argument has precedence over connection string username
            username_string = username

        hostnames = get_host_names_for_uri_dict(uri_dict=uri_dict)

        if len(uri_dict["nodelist"]) > 1:
            host_string = "%s (replica set)" % (hostnames)
        else:
            host_string = hostnames
    else:
        host_string = "%s:%s" % (db_host, db_port)
        username_string = username

    LOG.info(
        'Connecting to database "%s" @ "%s" as user "%s".'
        % (db_name, host_string, str(username_string))
    )

    ssl_kwargs = _get_ssl_kwargs(
        ssl=ssl,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
        authentication_mechanism=authentication_mechanism,
        ssl_match_hostname=ssl_match_hostname,
    )

    compressor_kwargs = {}

    if cfg.CONF.database.compressors:
        compressor_kwargs["compressors"] = cfg.CONF.database.compressors

    if cfg.CONF.database.zlib_compression_level is not None:
        compressor_kwargs[
            "zlibCompressionLevel"
        ] = cfg.CONF.database.zlib_compression_level

    # NOTE: We intentionally set "serverSelectionTimeoutMS" to 3 seconds. By default it's set to
    # 30 seconds, which means it will block up to 30 seconds and fail if there are any SSL related
    # or other errors
    connection_timeout = cfg.CONF.database.connection_timeout
    connection = mongoengine.connection.connect(
        db_name,
        host=db_host,
        port=db_port,
        tz_aware=True,
        username=username,
        password=password,
        connectTimeoutMS=connection_timeout,
        serverSelectionTimeoutMS=connection_timeout,
        **ssl_kwargs,
        **compressor_kwargs,
    )

    # NOTE: Since pymongo 3.0, connect() method is lazy and not blocking (always returns success)
    # so we need to issue a command / query to check if connection has been
    # successfully established.
    # See http://api.mongodb.com/python/current/api/pymongo/mongo_client.html for details
    try:
        # The ping command is cheap and does not require auth
        # https://www.mongodb.com/community/forums/t/how-to-use-the-new-hello-interface-for-availability/116748/
        connection.admin.command("ping")
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        # NOTE: ServerSelectionTimeoutError can also be thrown if SSLHandShake fails in the server
        # Sadly the client doesn't include more information about the error so in such scenarios
        # user needs to check MongoDB server log
        LOG.error(
            'Failed to connect to database "%s" @ "%s" as user "%s": %s'
            % (db_name, host_string, str(username_string), six.text_type(e))
        )
        raise e

    LOG.info(
        'Successfully connected to database "%s" @ "%s" as user "%s".'
        % (db_name, host_string, str(username_string))
    )

    return connection


def db_setup(
    db_name,
    db_host,
    db_port,
    username=None,
    password=None,
    ensure_indexes=True,
    ssl=False,
    ssl_keyfile=None,
    ssl_certfile=None,
    ssl_cert_reqs=None,
    ssl_ca_certs=None,
    authentication_mechanism=None,
    ssl_match_hostname=True,
):

    connection = _db_connect(
        db_name,
        db_host,
        db_port,
        username=username,
        password=password,
        ssl=ssl,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
        authentication_mechanism=authentication_mechanism,
        ssl_match_hostname=ssl_match_hostname,
    )

    # Create all the indexes upfront to prevent race-conditions caused by
    # lazy index creation
    if ensure_indexes:
        db_ensure_indexes()

    return connection


def db_ensure_indexes(model_classes=None):
    """
    This function ensures that indexes for all the models have been created and the
    extra indexes cleaned up.

    Note #1: When calling this method database connection already needs to be
    established.

    Note #2: This method blocks until all the index have been created (indexes
    are created in real-time and not in background).

    :param model_classes: DB model classes to ensure indexes for. If not specified, indexes are
                          ensured for all the models.
    :type model_classes: ``list``
    """
    LOG.debug("Ensuring database indexes...")

    if not model_classes:
        model_classes = get_model_classes()

    for model_class in model_classes:
        class_name = model_class.__name__

        # Note: We need to ensure / create new indexes before removing extra ones
        try:
            model_class.ensure_indexes()
        except OperationFailure as e:
            # Special case for "uid" index. MongoDB 3.4 has dropped "_types" index option so we
            # need to re-create the index to make it work and avoid "index with different options
            # already exists" error.
            # Note: This condition would only be encountered when upgrading existing StackStorm
            # installation from MongoDB 3.2 to 3.4.
            msg = six.text_type(e)
            if "already exists with different options" in msg and "uid_1" in msg:
                drop_obsolete_types_indexes(model_class=model_class)
            else:
                raise e
        except Exception as e:
            tb_msg = traceback.format_exc()
            msg = 'Failed to ensure indexes for model "%s": %s' % (
                class_name,
                six.text_type(e),
            )
            msg += "\n\n" + tb_msg
            exc_cls = type(e)
            raise exc_cls(msg)

        if model_class.__name__ in INDEX_CLEANUP_MODEL_NAMES_BLACKLIST:
            LOG.debug(
                'Skipping index cleanup for blacklisted model "%s"...' % (class_name)
            )
            continue

        removed_count = cleanup_extra_indexes(model_class=model_class)
        if removed_count:
            LOG.debug(
                'Removed "%s" extra indexes for model "%s"'
                % (removed_count, class_name)
            )

    LOG.debug(
        "Indexes are ensured for models: %s"
        % ", ".join(sorted((model_class.__name__ for model_class in model_classes)))
    )


def cleanup_extra_indexes(model_class):
    """
    Finds any extra indexes and removes those from mongodb.
    """
    extra_indexes = model_class.compare_indexes().get("extra", None)
    if not extra_indexes:
        return 0

    # mongoengine does not have the necessary method so we need to drop to
    # pymongo interfaces via some private methods.
    removed_count = 0
    c = model_class._get_collection()
    for extra_index in extra_indexes:
        try:
            c.drop_index(extra_index)
            LOG.debug(
                "Dropped index %s for model %s.", extra_index, model_class.__name__
            )
            removed_count += 1
        except OperationFailure:
            LOG.warning(
                "Attempt to cleanup index %s failed.", extra_index, exc_info=True
            )

    return removed_count


def drop_obsolete_types_indexes(model_class):
    """
    Special class for droping offending "types" indexes for which support has
    been removed in mongoengine and MongoDB 3.4.
    For more info, see: http://docs.mongoengine.org/upgrade.html#inheritance
    """
    class_name = model_class.__name__

    LOG.debug('Dropping obsolete types index for model "%s"' % (class_name))
    collection = model_class._get_collection()
    collection.update({}, {"$unset": {"_types": 1}}, multi=True)

    info = collection.index_information()
    indexes_to_drop = [
        key
        for key, value in six.iteritems(info)
        if "_types" in dict(value["key"]) or "types" in value
    ]

    LOG.debug(
        'Will drop obsolete types indexes for model "%s": %s'
        % (class_name, str(indexes_to_drop))
    )

    for index in indexes_to_drop:
        collection.drop_index(index)

    LOG.debug('Recreating indexes for model "%s"' % (class_name))
    model_class.ensure_indexes()


def db_teardown():
    mongoengine.connection.disconnect()


def db_cleanup(
    db_name,
    db_host,
    db_port,
    username=None,
    password=None,
    ssl=False,
    ssl_keyfile=None,
    ssl_certfile=None,
    ssl_cert_reqs=None,
    ssl_ca_certs=None,
    authentication_mechanism=None,
    ssl_match_hostname=True,
):

    connection = _db_connect(
        db_name,
        db_host,
        db_port,
        username=username,
        password=password,
        ssl=ssl,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
        authentication_mechanism=authentication_mechanism,
        ssl_match_hostname=ssl_match_hostname,
    )

    LOG.info(
        'Dropping database "%s" @ "%s:%s" as user "%s".',
        db_name,
        db_host,
        db_port,
        str(username),
    )

    connection.drop_database(db_name)
    return connection


def _get_ssl_kwargs(
    ssl=False,
    ssl_keyfile=None,
    ssl_certfile=None,
    ssl_cert_reqs=None,
    ssl_ca_certs=None,
    authentication_mechanism=None,
    ssl_match_hostname=True,
):
    # NOTE: In pymongo 3.9.0 some of the ssl related arguments have been renamed -
    # https://api.mongodb.com/python/current/changelog.html#changes-in-version-3-9-0
    # Old names still work, but we should eventually update to new argument names.
    ssl_kwargs = {
        "ssl": ssl,
    }
    if ssl_keyfile:
        ssl_kwargs["ssl"] = True
        ssl_kwargs["ssl_keyfile"] = ssl_keyfile
    if ssl_certfile:
        ssl_kwargs["ssl"] = True
        ssl_kwargs["ssl_certfile"] = ssl_certfile
    if ssl_cert_reqs:
        if ssl_cert_reqs == "none":
            ssl_cert_reqs = ssl_lib.CERT_NONE
        elif ssl_cert_reqs == "optional":
            ssl_cert_reqs = ssl_lib.CERT_OPTIONAL
        elif ssl_cert_reqs == "required":
            ssl_cert_reqs = ssl_lib.CERT_REQUIRED
        ssl_kwargs["ssl_cert_reqs"] = ssl_cert_reqs
    if ssl_ca_certs:
        ssl_kwargs["ssl"] = True
        ssl_kwargs["ssl_ca_certs"] = ssl_ca_certs
    if authentication_mechanism:
        ssl_kwargs["ssl"] = True
        ssl_kwargs["authentication_mechanism"] = authentication_mechanism
    if ssl_kwargs.get("ssl", False):
        # pass in ssl_match_hostname only if ssl is True. The right default value
        # for ssl_match_hostname in almost all cases is True.
        ssl_kwargs["ssl_match_hostname"] = ssl_match_hostname
    return ssl_kwargs


class MongoDBAccess(object):
    """Database object access class that provides general functions for a model type."""

    def __init__(self, model):
        self.model = model

    def get_by_name(self, value):
        return self.get(name=value, raise_exception=True)

    def get_by_id(self, value):
        return self.get(id=value, raise_exception=True)

    def get_by_uid(self, value):
        return self.get(uid=value, raise_exception=True)

    def get_by_ref(self, value):
        return self.get(ref=value, raise_exception=True)

    def get_by_pack(self, value):
        return self.get(pack=value, raise_exception=True)

    def get(self, *args, **kwargs):
        exclude_fields = kwargs.pop("exclude_fields", None)
        raise_exception = kwargs.pop("raise_exception", False)
        only_fields = kwargs.pop("only_fields", None)

        args = self._process_arg_filters(args)

        instances = self.model.objects(*args, **kwargs)

        if exclude_fields:
            instances = instances.exclude(*exclude_fields)

        if only_fields:
            try:
                instances = instances.only(*only_fields)
            except (mongoengine.errors.LookUpError, AttributeError) as e:
                msg = (
                    "Invalid or unsupported include attribute specified: %s"
                    % six.text_type(e)
                )
                raise ValueError(msg)

        instance = instances[0] if instances else None
        log_query_and_profile_data_for_queryset(queryset=instances)

        if not instance and raise_exception:
            msg = "Unable to find the %s instance. %s" % (self.model.__name__, kwargs)
            raise db_exc.StackStormDBObjectNotFoundError(msg)

        return instance

    def get_all(self, *args, **kwargs):
        return self.query(*args, **kwargs)

    def count(self, *args, **kwargs):
        result = self.model.objects(*args, **kwargs).count()
        log_query_and_profile_data_for_queryset(queryset=result)
        return result

    # TODO: PEP-3102 introduced keyword-only arguments, so once we support Python 3+, we can change
    #       this definition to have explicit keyword-only arguments:
    #
    #           def query(self, *args, offset=0, limit=None, order_by=None, exclude_fields=None,
    #                     **filters):
    def query(self, *args, **filters):
        # Python 2: Pop keyword parameters that aren't actually filters off of the kwargs
        offset = filters.pop("offset", 0)
        limit = filters.pop("limit", None)
        order_by = filters.pop("order_by", None)
        exclude_fields = filters.pop("exclude_fields", None)
        only_fields = filters.pop("only_fields", None)
        no_dereference = filters.pop("no_dereference", None)

        order_by = order_by or []
        exclude_fields = exclude_fields or []
        eop = offset + int(limit) if limit else None

        args = self._process_arg_filters(args)
        # Process the filters
        # Note: Both of those functions manipulate "filters" variable so the order in which they
        # are called matters
        filters, order_by = self._process_datetime_range_filters(
            filters=filters, order_by=order_by
        )
        filters = self._process_null_filters(filters=filters)

        result = self.model.objects(*args, **filters)

        if exclude_fields:
            try:
                result = result.exclude(*exclude_fields)
            except (mongoengine.errors.LookUpError, AttributeError) as e:
                field = get_field_name_from_mongoengine_error(e)
                msg = "Invalid or unsupported exclude attribute specified: %s" % field
                raise ValueError(msg)

        if only_fields:
            try:
                result = result.only(*only_fields)
            except (mongoengine.errors.LookUpError, AttributeError) as e:
                field = get_field_name_from_mongoengine_error(e)
                msg = "Invalid or unsupported include attribute specified: %s" % field
                raise ValueError(msg)

        if no_dereference:
            result = result.no_dereference()

        result = result.order_by(*order_by)
        result = result[offset:eop]
        log_query_and_profile_data_for_queryset(queryset=result)

        return result

    def distinct(self, *args, **kwargs):
        field = kwargs.pop("field")
        result = self.model.objects(**kwargs).distinct(field)
        log_query_and_profile_data_for_queryset(queryset=result)
        return result

    def aggregate(self, *args, **kwargs):
        return self.model.objects(**kwargs)._collection.aggregate(*args, **kwargs)

    def insert(self, instance):
        instance = self.model.objects.insert(instance)
        return self._undo_dict_field_escape(instance)

    def add_or_update(self, instance, validate=True):
        instance.save(validate=validate)
        return self._undo_dict_field_escape(instance)

    def update(self, instance, **kwargs):
        return instance.update(**kwargs)

    def delete(self, instance):
        return instance.delete()

    def delete_by_query(self, *args, **query):
        """
        Delete objects by query and return number of deleted objects.
        """
        qs = self.model.objects.filter(*args, **query)
        count = qs.delete()
        log_query_and_profile_data_for_queryset(queryset=qs)

        return count

    def _undo_dict_field_escape(self, instance):
        for attr, field in six.iteritems(instance._fields):
            if isinstance(field, stormbase.EscapedDictField):
                value = getattr(instance, attr)
                setattr(instance, attr, field.to_python(value))
        return instance

    def _process_arg_filters(self, args):
        """
        Fix filter arguments in nested Q objects
        """
        _args = tuple()

        for arg in args:
            # Unforunately mongoengine doesn't expose any visitors other than Q, so we have to
            # extract QCombination from the module itself
            if isinstance(arg, visitor.Q):
                # Note: Both of those functions manipulate "filters" variable so the order in which
                # they are called matters
                filters, _ = self._process_datetime_range_filters(filters=arg.query)
                filters = self._process_null_filters(filters=filters)

                # Create a new Q object with the same filters as the old one
                _args += (visitor.Q(**filters),)
            elif isinstance(arg, visitor.QCombination):
                # Recurse if we need to
                children = self._process_arg_filters(arg.children)

                # Create a new QCombination object with the same operation and fixed filters
                _args += (visitor.QCombination(arg.operation, children),)
            else:
                raise TypeError(
                    "Unknown argument type '%s' of argument '%s'"
                    % (type(arg), repr(arg))
                )

        return _args

    def _process_null_filters(self, filters):
        result = copy.deepcopy(filters)

        null_filters = {}

        for key, value in six.iteritems(filters):
            if value is None:
                null_filters[key] = value
            elif isinstance(value, (str, six.text_type)) and value.lower() == "null":
                null_filters[key] = value
            else:
                continue

        for key in null_filters.keys():
            result["%s__exists" % (key)] = False
            del result[key]

        return result

    def _process_datetime_range_filters(self, filters, order_by=None):
        ranges = {
            k: v
            for k, v in six.iteritems(filters)
            if type(v) in [str, six.text_type] and ".." in v
        }

        order_by_list = copy.deepcopy(order_by) if order_by else []
        for k, v in six.iteritems(ranges):
            values = v.split("..")
            dt1 = isotime.parse(values[0])
            dt2 = isotime.parse(values[1])

            k__gte = "%s__gte" % k
            k__lte = "%s__lte" % k
            if dt1 < dt2:
                query = {k__gte: dt1, k__lte: dt2}
                sort_key, reverse_sort_key = k, "-" + k
            else:
                query = {k__gte: dt2, k__lte: dt1}
                sort_key, reverse_sort_key = "-" + k, k
            del filters[k]
            filters.update(query)

            if reverse_sort_key in order_by_list:
                idx = order_by_list.index(reverse_sort_key)
                order_by_list.pop(idx)
                order_by_list.insert(idx, sort_key)
            elif sort_key not in order_by_list:
                order_by_list = [sort_key] + order_by_list

        return filters, order_by_list


class ChangeRevisionMongoDBAccess(MongoDBAccess):
    def insert(self, instance):
        instance = self.model.objects.insert(instance)

        return self._undo_dict_field_escape(instance)

    def add_or_update(self, instance, validate=True):
        return self.save(instance, validate=validate)

    def update(self, instance, **kwargs):
        for k, v in six.iteritems(kwargs):
            setattr(instance, k, v)

        return self.save(instance)

    def save(self, instance, validate=True):
        if not hasattr(instance, "id") or not instance.id:
            return self.insert(instance)
        else:
            try:
                save_condition = {"id": instance.id, "rev": instance.rev}
                instance.rev = instance.rev + 1
                instance.save(save_condition=save_condition, validate=validate)
            except mongoengine.SaveConditionError:
                raise db_exc.StackStormDBObjectWriteConflictError(instance)

            return self._undo_dict_field_escape(instance)


def get_host_names_for_uri_dict(uri_dict):
    hosts = []

    for host, port in uri_dict["nodelist"]:
        hosts.append("%s:%s" % (host, port))

    hosts = ",".join(hosts)
    return hosts
