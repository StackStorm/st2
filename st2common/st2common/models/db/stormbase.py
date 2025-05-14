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
import datetime

import bson
import six
import mongoengine as me
from mongoengine.pymongo_support import LEGACY_JSON_OPTIONS
from oslo_config import cfg

from st2common.util import mongoescape
from st2common.models.base import DictSerializableClassMixin
from st2common.models.system.common import ResourceReference
from st2common.constants.types import ResourceType
from st2common.util.jsonify import json_decode

__all__ = [
    "StormFoundationDB",
    "StormBaseDB",
    "EscapedDictField",
    "EscapedDynamicField",
    "TagField",
    "RefFieldMixin",
    "UIDFieldMixin",
    "TagsMixin",
    "ContentPackResourceMixin",
]

JSON_UNFRIENDLY_TYPES = (datetime.datetime, bson.ObjectId)

DICT_FIELD_NOT_SET_MARKER = "dict-field-not-set"


class StormFoundationDB(me.Document, DictSerializableClassMixin):
    """
    Base abstraction for a model entity. This foundation class should only be directly
    inherited from the application domain models.
    """

    # Variable representing a type of this resource
    RESOURCE_TYPE = ResourceType.UNKNOWN

    # We explicitly assign the manager so pylint know what type objects is
    objects = me.queryset.QuerySetManager()

    # Note: In mongoengine >= 0.10 "id" field is automatically declared on all
    # the documents and declaring it ourselves causes a lot of issues so we
    # don't do that

    # see http://docs.mongoengine.org/guide/defining-documents.html#abstract-classes
    meta = {"abstract": True}

    def __str__(self):
        attrs = list()
        for k in sorted(self._fields.keys()):  # pylint: disable=E1101
            v = getattr(self, k)
            v = (
                '"%s"' % str(v)
                if type(v) in [str, six.text_type, datetime.datetime]
                else str(v)
            )
            attrs.append("%s=%s" % (k, v))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(attrs))

    def get_resource_type(self):
        return self.RESOURCE_TYPE

    def mask_secrets(self, value):
        """
        Process the model dictionary and mask secret values.

        :type value: ``dict``
        :param value: Document dictionary.

        :rtype: ``dict``
        """
        return value

    def to_serializable_dict(self, mask_secrets=False):
        """
        Serialize database model to a dictionary.

        :param mask_secrets: True to mask secrets in the resulting dict.
        :type mask_secrets: ``boolean``

        :rtype: ``dict``
        """
        serializable_dict = {}
        for k in sorted(six.iterkeys(self._fields)):  # pylint: disable=E1101
            v = getattr(self, k)
            if isinstance(v, JSON_UNFRIENDLY_TYPES):
                v = str(v)
            elif isinstance(v, me.EmbeddedDocument):
                # TODO: Allow overriding json_options.uuid_representation via cfg
                v = json_decode(v.to_json(json_options=LEGACY_JSON_OPTIONS))

            serializable_dict[k] = v

        if mask_secrets and cfg.CONF.log.mask_secrets:
            serializable_dict = self.mask_secrets(value=serializable_dict)

        return serializable_dict


class StormBaseDB(StormFoundationDB):
    """Abstraction for a user content model."""

    name = me.StringField(required=True, unique=True)
    description = me.StringField()

    # see http://docs.mongoengine.org/guide/defining-documents.html#abstract-classes
    meta = {"abstract": True}


class EscapedDictField(me.DictField):
    def to_mongo(self, value, use_db_field=True, fields=None):
        value = mongoescape.escape_chars(value)
        return super(EscapedDictField, self).to_mongo(
            value=value, use_db_field=use_db_field, fields=fields
        )

    def to_python(self, value):
        value = super(EscapedDictField, self).to_python(value)
        return mongoescape.unescape_chars(value)

    def validate(self, value):
        if not isinstance(value, dict):
            self.error("Only dictionaries may be used in a DictField")
        if me.fields.key_not_string(value):
            self.error("Invalid dictionary key - documents must have only string keys")
        me.base.ComplexBaseField.validate(self, value)


class EscapedDynamicField(me.DynamicField):
    def to_mongo(self, value, use_db_field=True, fields=None):
        value = mongoescape.escape_chars(value)
        return super(EscapedDynamicField, self).to_mongo(
            value=value, use_db_field=use_db_field, fields=fields
        )

    def to_python(self, value):
        value = super(EscapedDynamicField, self).to_python(value)
        return mongoescape.unescape_chars(value)


class TagField(me.EmbeddedDocument):
    """
    To be attached to a db model object for the purpose of providing supplemental
    information.
    """

    name = me.StringField(max_length=1024)
    value = me.StringField(max_length=1024)


class TagsMixin(object):
    """
    Mixin to include tags on an object.
    """

    tags = me.ListField(field=me.EmbeddedDocumentField(TagField))

    @classmethod
    def get_indexes(cls):
        return ["tags.name", "tags.value"]


class RefFieldMixin(object):
    """
    Mixin class which adds "ref" field to the class inheriting from it.
    """

    ref = me.StringField(required=True, unique=True)


class UIDFieldMixin(object):
    """
    Mixin class which adds "uid" field to the class inheriting from it.

    UID field is a unique identifier which we can be used to unambiguously reference a resource in
    the system.
    """

    UID_SEPARATOR = ":"  # TODO: Move to constants

    RESOURCE_TYPE = abc.abstractproperty
    UID_FIELDS = abc.abstractproperty

    uid = me.StringField(required=True)

    @classmethod
    def get_indexes(cls):
        # Note: We use a special sparse index so we don't need to pre-populate "uid" for existing
        # models in the database before ensure_indexes() is called.
        # This field gets populated in the constructor which means it will be lazily assigned next
        # time the model is saved (e.g. once register-content is ran).
        indexes = [{"fields": ["uid"], "unique": True, "sparse": True}]
        return indexes

    def get_uid(self):
        """
        Return an object UID constructed from the object properties / fields.

        :rtype: ``str``
        """
        parts = []
        parts.append(self.RESOURCE_TYPE)

        for field in self.UID_FIELDS:
            value = getattr(self, field, None) or ""
            parts.append(value)

        uid = self.UID_SEPARATOR.join(parts)
        return uid

    def get_uid_parts(self):
        """
        Return values for fields which make up the UID.

        :rtype: ``list``
        """
        parts = self.uid.split(self.UID_SEPARATOR)  # pylint: disable=no-member
        parts = [part for part in parts if part.strip()]
        return parts

    def has_valid_uid(self):
        """
        Return True if object contains a valid id (aka all parts contain a valid value).

        :rtype: ``bool``
        """
        parts = self.get_uid_parts()
        return len(parts) == len(self.UID_FIELDS) + 1


class ContentPackResourceMixin(object):
    """
    Mixin class provides utility methods for models which belong to a pack.
    """

    metadata_file = me.StringField(
        required=False,
        help_text=(
            "Path to the metadata file (file on disk which contains resource definition) "
            "relative to the pack directory."
        ),
    )

    def get_pack_uid(self):
        """
        Return an UID of a pack this resource belongs to.

        :rtype ``str``
        """
        parts = [ResourceType.PACK, self.pack]
        uid = UIDFieldMixin.UID_SEPARATOR.join(parts)
        return uid

    def get_reference(self):
        """
        Retrieve referene object for this model.

        :rtype: :class:`ResourceReference`
        """
        if getattr(self, "ref", None):
            ref = ResourceReference.from_string_reference(ref=self.ref)
        else:
            ref = ResourceReference(pack=self.pack, name=self.name)

        return ref

    @classmethod
    def get_indexes(cls):
        return [
            {
                "fields": ["metadata_file"],
            }
        ]


class ChangeRevisionFieldMixin(object):

    rev = me.IntField(required=True, default=1)

    @classmethod
    def get_indexes(cls):
        return [{"fields": ["id", "rev"], "unique": True}]
