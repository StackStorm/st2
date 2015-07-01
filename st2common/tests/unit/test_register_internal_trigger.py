# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from st2common.persistence.trigger import Trigger
from st2common.triggers import register_internal_trigger_types
from st2tests.base import DbTestCase


class TestRegisterInternalTriggers(DbTestCase):

    def test_register_internal_trigger_types(self):
        registered_trigger_types_db = register_internal_trigger_types()
        for trigger_type_db in registered_trigger_types_db:
            self._validate_shadow_trigger(trigger_type_db)

    def _validate_shadow_trigger(self, trigger_type_db):
        if trigger_type_db.parameters_schema:
            return
        trigger_type_ref = trigger_type_db.get_reference().ref
        triggers = Trigger.query(type=trigger_type_ref)
        self.assertTrue(len(triggers) > 0, 'Shadow trigger not created for %s.' % trigger_type_ref)
