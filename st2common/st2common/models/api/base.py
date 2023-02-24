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
import abc

import six

from oslo_config import cfg

from st2common.util import mongoescape as util_mongodb
from st2common import log as logging

__all__ = ["BaseAPI", "APIUIDMixin"]


LOG = logging.getLogger(__name__)


# NOTE: Update pylint_plugins/fixtures/api_models.py if this changes significantly
@six.add_metaclass(abc.ABCMeta)
class BaseAPI(object):
    schema = abc.abstractproperty
    name = None

    # A list of document fields on which we should not call unescape_chars. Right now we should
    # manually list all the JSONDict field types here, but in the future we should improve the code
    # to explicitly call unescape only on EscapedDict/DynamicField values (this requires bigger
    # change).
    skip_unescape_field_names = []

    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)

    def __repr__(self):
        name = type(self).__name__
        attrs = ", ".join("'%s': %r" % item for item in six.iteritems(vars(self)))
        # The format here is so that eval can be applied.
        return "%s(**{%s})" % (name, attrs)

    def __str__(self):
        name = type(self).__name__
        attrs = ", ".join("%s=%r" % item for item in six.iteritems(vars(self)))

        return "%s[%s]" % (name, attrs)

    def __json__(self):
        return vars(self)

    def validate(self):
        """
        Perform validation and return cleaned object on success.

        Note: This method doesn't mutate this object in place, but it returns a new one.

        :return: Cleaned / validated object.
        """
        from st2common.util import schema as util_schema

        schema = getattr(self, "schema", {})
        attributes = vars(self)

        cleaned = util_schema.validate(
            instance=attributes,
            schema=schema,
            cls=util_schema.CustomValidator,
            use_default=True,
            allow_default_none=True,
        )

        # Note: We use type() instead of self.__class__ since self.__class__ confuses pylint
        return type(self)(**cleaned)

    @classmethod
    def _from_model(cls, model, mask_secrets=False):
        doc = model.to_mongo()

        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))

        # Special case for models which utilize JSONDictField - there is no need to escape those
        # fields since it contains a JSON string and not a dictionary which doesn't need to be
        # mongo escaped. Skipping this step here substantially speeds things up for that field.

        # Right now we do this here manually for all those fields types but eventually we should
        # refactor the code to just call unescape chars on escaped fields - more generic and
        # faster.
        raw_values = {}

        for field_name in cls.skip_unescape_field_names:
            if isinstance(doc.get(field_name, None), bytes):
                raw_values[field_name] = doc.pop(field_name)

        # TODO (Tomaz): In general we really shouldn't need to call unescape chars on the whole doc,
        # but just on the EscapedDict and EscapedDynamicField fields - doing it on the whole doc
        # level is slow and not necessary!
        doc = util_mongodb.unescape_chars(doc)

        # Now add the JSON string field value which shouldn't be escaped back.
        # We don't JSON parse the field value here because that happens inside the model specific
        # "from_model()" method where we also parse and convert all the other field values.
        for field_name, field_value in raw_values.items():
            doc[field_name] = field_value

        if mask_secrets and cfg.CONF.log.mask_secrets:
            doc = model.mask_secrets(value=doc)

        return doc

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        """
        Create API model class instance for the provided DB model instance.

        :param model: DB model class instance.
        :type model: :class:`StormFoundationDB`

        :param mask_secrets: True to mask secrets in the resulting instance.
        :type mask_secrets: ``boolean``
        """
        doc = cls._from_model(model=model, mask_secrets=mask_secrets)
        attrs = {attr: value for attr, value in six.iteritems(doc) if value is not None}

        return cls(**attrs)

    @classmethod
    def to_model(cls, doc):
        """
        Create a model class instance for the provided MongoDB document.

        :param doc: MongoDB document.
        """
        raise NotImplementedError()


class APIUIDMixin(object):
    """ "
    Mixin class for retrieving UID for API objects.
    """

    def get_uid(self):
        # TODO: This is not the most efficient approach - refactor this functionality into util
        # module and re-use it here and in the DB model
        resource_db = self.to_model(self)
        resource_uid = resource_db.get_uid()
        return resource_uid

    def get_pack_uid(self):
        # TODO: This is not the most efficient approach - refactor this functionality into util
        # module and re-use it here and in the DB model
        resource_db = self.to_model(self)
        pack_uid = resource_db.get_pack_uid()
        return pack_uid

    def has_valid_uid(self):
        resource_db = self.to_model(self)
        return resource_db.has_valid_uid()


def cast_argument_value(value_type, value):
    if value_type == bool:

        def cast_func(value):
            value = str(value)
            return value.lower() in ["1", "true"]

    else:
        cast_func = value_type

    result = cast_func(value)
    return result
