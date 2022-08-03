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

# pytest: make sure monkey_patching happens before importing mongoengine
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import mongoengine

from st2common.models.db import stormbase
from st2common.util import date as date_utils
from st2tests import DbTestCase


class FakeRuleSpecDB(mongoengine.EmbeddedDocument):
    ref = mongoengine.StringField(required=True, unique=False)
    parameters = mongoengine.DictField()

    def __str__(self):
        result = []
        result.append("ActionExecutionSpecDB@")
        result.append("test")
        result.append('(ref="%s", ' % self.ref)
        result.append('parameters="%s")' % self.parameters)
        return "".join(result)


class FakeModel(stormbase.StormBaseDB):
    boolean_field = mongoengine.BooleanField()
    datetime_field = mongoengine.DateTimeField()
    dict_field = mongoengine.DictField()
    integer_field = mongoengine.IntField()
    list_field = mongoengine.ListField()


class FakeRuleModel(stormbase.StormBaseDB):
    boolean_field = mongoengine.BooleanField()
    datetime_field = mongoengine.DateTimeField()
    dict_field = mongoengine.DictField()
    integer_field = mongoengine.IntField()
    list_field = mongoengine.ListField()
    embedded_doc_field = mongoengine.EmbeddedDocumentField(FakeRuleSpecDB)


class TestBaseModel(DbTestCase):
    def test_print(self):
        instance = FakeModel(
            name="seesaw",
            boolean_field=True,
            datetime_field=date_utils.get_datetime_utc_now(),
            description="fun!",
            dict_field={"a": 1},
            integer_field=68,
            list_field=["abc"],
        )

        expected = (
            'FakeModel(boolean_field=True, datetime_field="%s", description="fun!", '
            "dict_field={'a': 1}, id=None, integer_field=68, list_field=['abc'], "
            'name="seesaw")' % str(instance.datetime_field)
        )

        self.assertEqual(str(instance), expected)

    def test_rule_print(self):
        instance = FakeRuleModel(
            name="seesaw",
            boolean_field=True,
            datetime_field=date_utils.get_datetime_utc_now(),
            description="fun!",
            dict_field={"a": 1},
            integer_field=68,
            list_field=["abc"],
            embedded_doc_field={"ref": "1234", "parameters": {"b": 2}},
        )

        expected = (
            'FakeRuleModel(boolean_field=True, datetime_field="%s", description="fun!", '
            "dict_field={'a': 1}, embedded_doc_field=ActionExecutionSpecDB@test("
            'ref="1234", parameters="{\'b\': 2}"), id=None, integer_field=68, '
            "list_field=['abc'], "
            'name="seesaw")' % str(instance.datetime_field)
        )

        self.assertEqual(str(instance), expected)
