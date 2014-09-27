import datetime

import mongoengine

from st2common.models.db import stormbase
from st2tests import DbTestCase


class FakeModel(stormbase.StormBaseDB):
    boolean_field = mongoengine.BooleanField()
    datetime_field = mongoengine.DateTimeField()
    dict_field = mongoengine.DictField()
    integer_field = mongoengine.IntField()
    list_field = mongoengine.ListField()


class TestBaseModel(DbTestCase):

    def test_print(self):
        instance = FakeModel(name='seesaw', boolean_field=True,
                             datetime_field=datetime.datetime.now(),
                             description=u'fun!', dict_field={'a': 1},
                             integer_field=68, list_field=['abc'])

        expected = ('FakeModel@%s(boolean_field=True, datetime_field="%s", description="fun!", '
                    'dict_field={\'a\': 1}, id=None, integer_field=68, list_field=[\'abc\'], '
                    'name="seesaw")' % (id(instance), str(instance.datetime_field)))

        self.assertEqual(str(instance), expected)
