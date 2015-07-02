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

import mongoengine

from st2common.models.db import stormbase
from st2common.util import date as date_utils
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
                             datetime_field=date_utils.get_datetime_utc_now(),
                             description=u'fun!', dict_field={'a': 1},
                             integer_field=68, list_field=['abc'])

        expected = ('FakeModel(boolean_field=True, datetime_field="%s", description="fun!", '
                    'dict_field={\'a\': 1}, id=None, integer_field=68, list_field=[\'abc\'], '
                    'name="seesaw")' % str(instance.datetime_field))

        self.assertEqual(str(instance), expected)
