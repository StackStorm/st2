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
import bson

from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.persistence.executionstate import ActionExecutionState
from st2common.exceptions.db import StackStormDBObjectNotFoundError

from st2tests import DbTestCase


class ActionExecutionStateTests(DbTestCase):
    def test_state_crud(self):
        saved = ActionExecutionStateTests._create_save_actionstate()
        retrieved = ActionExecutionState.get_by_id(saved.id)
        self.assertDictEqual(saved.query_context, retrieved.query_context)
        self.assertEqual(saved.query_module, retrieved.query_module)
        ActionExecutionStateTests._delete(model_objects=[retrieved])
        try:
            retrieved = ActionExecutionState.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, "managed to retrieve after failure.")

    @staticmethod
    def _create_save_actionstate():
        created = ActionExecutionStateDB()
        created.query_context = {"id": "some_external_service_id"}
        created.query_module = "dummy.modules.query1"
        created.execution_id = bson.ObjectId()
        return ActionExecutionState.add_or_update(created)

    @staticmethod
    def _delete(model_objects=[]):
        for model_object in model_objects:
            model_object.delete()
