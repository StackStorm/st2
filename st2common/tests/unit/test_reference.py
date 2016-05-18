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

import copy
import mock
import mongoengine

from st2common.exceptions import db
from st2common.models.db.trigger import TriggerDB
from st2common.persistence.trigger import Trigger
from st2common.transport.publishers import PoolPublisher
from st2common.util import reference
from st2tests import DbTestCase


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ReferenceTest(DbTestCase):

    __model = None
    __ref = None

    @classmethod
    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def setUpClass(cls):
        super(ReferenceTest, cls).setUpClass()
        trigger = TriggerDB(pack='dummy_pack_1', name='trigger-1')
        cls.__model = Trigger.add_or_update(trigger)
        cls.__ref = {'id': str(cls.__model.id),
                     'name': cls.__model.name}

    @classmethod
    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def tearDownClass(cls):
        Trigger.delete(cls.__model)
        super(ReferenceTest, cls).tearDownClass()

    def test_to_reference(self):
        ref = reference.get_ref_from_model(self.__model)
        self.assertEqual(ref, self.__ref, 'Failed to generated equivalent ref.')

    def test_to_reference_no_model(self):
        try:
            reference.get_ref_from_model(None)
            self.assertTrue(False, 'Exception expected.')
        except ValueError:
            self.assertTrue(True)

    def test_to_reference_no_model_id(self):
        try:
            model = copy.copy(self.__model)
            model.id = None
            reference.get_ref_from_model(model)
            self.assertTrue(False, 'Exception expected.')
        except db.StackStormDBObjectMalformedError:
            self.assertTrue(True)

    def test_to_model_with_id(self):
        model = reference.get_model_from_ref(Trigger, self.__ref)
        self.assertEqual(model, self.__model, 'Failed to return correct model.')

    def test_to_model_with_name(self):
        ref = copy.copy(self.__ref)
        ref['id'] = None
        model = reference.get_model_from_ref(Trigger, ref)
        self.assertEqual(model, self.__model, 'Failed to return correct model.')

    def test_to_model_no_name_no_id(self):
        try:
            reference.get_model_from_ref(Trigger, {})
            self.assertTrue(False, 'Exception expected.')
        except db.StackStormDBObjectNotFoundError:
            self.assertTrue(True)

    def test_to_model_unknown_id(self):
        try:
            reference.get_model_from_ref(Trigger, {'id': '1'})
            self.assertTrue(False, 'Exception expected.')
        except mongoengine.ValidationError:
            self.assertTrue(True)

    def test_to_model_unknown_name(self):
        try:
            reference.get_model_from_ref(Trigger, {'name': 'unknown'})
            self.assertTrue(False, 'Exception expected.')
        except db.StackStormDBObjectNotFoundError:
            self.assertTrue(True)
