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

from datetime import timedelta

from st2common import log as logging
from st2common.constants.triggers import TRIGGER_INSTANCE_PROCESSED
from st2common.garbage_collection.trigger_instances import purge_trigger_instances
from st2common.models.db.trigger import TriggerInstanceDB
from st2common.persistence.trigger import TriggerInstance
from st2common.util import date as date_utils
from st2tests.base import CleanDbTestCase

LOG = logging.getLogger(__name__)


class TestPurgeTriggerInstances(CleanDbTestCase):

    @classmethod
    def setUpClass(cls):
        CleanDbTestCase.setUpClass()
        super(TestPurgeTriggerInstances, cls).setUpClass()

    def setUp(self):
        super(TestPurgeTriggerInstances, self).setUp()

    def test_no_timestamp_doesnt_delete(self):
        now = date_utils.get_datetime_utc_now()

        instance_db = TriggerInstanceDB(trigger='purge_tool.dummy.trigger',
                                        payload={'hola': 'hi', 'kuraci': 'chicken'},
                                        occurrence_time=now - timedelta(days=20),
                                        status=TRIGGER_INSTANCE_PROCESSED)
        TriggerInstance.add_or_update(instance_db)

        self.assertEqual(len(TriggerInstance.get_all()), 1)
        expected_msg = 'Specify a valid timestamp'
        self.assertRaisesRegexp(ValueError, expected_msg,
                                purge_trigger_instances,
                                logger=LOG, timestamp=None)
        self.assertEqual(len(TriggerInstance.get_all()), 1)

    def test_purge(self):
        now = date_utils.get_datetime_utc_now()

        instance_db = TriggerInstanceDB(trigger='purge_tool.dummy.trigger',
                                        payload={'hola': 'hi', 'kuraci': 'chicken'},
                                        occurrence_time=now - timedelta(days=20),
                                        status=TRIGGER_INSTANCE_PROCESSED)
        TriggerInstance.add_or_update(instance_db)

        instance_db = TriggerInstanceDB(trigger='purge_tool.dummy.trigger',
                                        payload={'hola': 'hi', 'kuraci': 'chicken'},
                                        occurrence_time=now - timedelta(days=5),
                                        status=TRIGGER_INSTANCE_PROCESSED)
        TriggerInstance.add_or_update(instance_db)

        self.assertEqual(len(TriggerInstance.get_all()), 2)
        purge_trigger_instances(logger=LOG, timestamp=now - timedelta(days=10))
        self.assertEqual(len(TriggerInstance.get_all()), 1)
