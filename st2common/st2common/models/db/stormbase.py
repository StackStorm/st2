# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

import bson
import six
import mongoengine as me

from st2common.util import mongoescape
from st2common.models.system.common import ResourceReference

__all__ = [
    'StormFoundationDB',
    'StormBaseDB',
    'EscapedDictField',
    'TagsMixin',
    'TagField',
    'ContentPackResourceMixin'
]

JSON_UNFRIENDLY_TYPES = (datetime.datetime, bson.ObjectId, me.EmbeddedDocument)


class StormFoundationDB(me.Document):
    """
    Base abstraction for a model entity. This foundation class should only be directly
    inherited from the application domain models.
    """

    # We explicitly assign the manager so pylint know what type objects is
    objects = me.queryset.QuerySetManager()

    # ObjectIdField should be not have any constraints like required,
    # unique etc for it to be auto-generated.
    # TODO: Work out how we can mark this as a unique primary key.
    id = me.ObjectIdField()

    # see http://docs.mongoengine.org/guide/defining-documents.html#abstract-classes
    meta = {
        'abstract': True
    }

    def __str__(self):
        attrs = list()
        for k in sorted(self._fields.keys()):
            v = getattr(self, k)
            v = '"%s"' % str(v) if type(v) in [str, unicode, datetime.datetime] else str(v)
            attrs.append('%s=%s' % (k, v))
        return '%s(%s)' % (self.__class__.__name__, ', '.join(attrs))

    def to_serializable_dict(self, exclude_secrets=False):
        """
        :rtype: ``dict``
        """
        serializable_dict = {}
        for k in sorted(six.iterkeys(self._fields)):
            v = getattr(self, k)
            v = str(v) if isinstance(v, JSON_UNFRIENDLY_TYPES) else v
            serializable_dict[k] = v
        return serializable_dict


class StormBaseDB(StormFoundationDB):
    """Abstraction for a user content model."""

    name = me.StringField(required=True, unique=True)
    description = me.StringField()

    # see http://docs.mongoengine.org/guide/defining-documents.html#abstract-classes
    meta = {
        'abstract': True
    }


class EscapedDictField(me.DictField):

    def to_mongo(self, value):
        value = mongoescape.escape_chars(value)
        return super(EscapedDictField, self).to_mongo(value)

    def to_python(self, value):
        value = super(EscapedDictField, self).to_python(value)
        return mongoescape.unescape_chars(value)

    def validate(self, value):
        if not isinstance(value, dict):
            self.error('Only dictionaries may be used in a DictField')
        if me.fields.key_not_string(value):
            self.error("Invalid dictionary key - documents must have only string keys")
        me.base.ComplexBaseField.validate(self, value)


class EscapedDynamicField(me.DynamicField):

    def to_mongo(self, value):
        value = mongoescape.escape_chars(value)
        return super(EscapedDynamicField, self).to_mongo(value)

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
    def get_indices(cls):
        return ['tags.name', 'tags.value']


class ContentPackResourceMixin(object):
    """
    Mixin class which provides utility methods for models which contain
    a "pack" attribute.
    """

    def get_reference(self):
        """
        Retrieve referene object for this model.

        :rtype: :class:`ResourceReference`
        """
        ref = ResourceReference(pack=self.pack, name=self.name)
        return ref
