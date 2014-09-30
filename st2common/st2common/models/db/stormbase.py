import datetime

import mongoengine as me

from st2common.util import mongoescape


class StormFoundationDB(me.Document):
    """
    Base abstraction for a model entity. This foundation class should only be directly
    inherited from the application domain models.
    """

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

    def to_python(self):
        return {attr: field.to_python(getattr(self, attr))
                for attr, field in self._fields.iteritems()
                if getattr(self, attr, None)}


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
