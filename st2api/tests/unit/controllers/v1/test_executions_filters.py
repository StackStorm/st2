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
import random
import datetime

import bson
import six
from six.moves import http_client

import st2tests.config as tests_config
tests_config.parse_args()

from st2tests.api import FunctionalTest
from st2tests.fixtures.packs import executions as fixture
from st2tests.fixtures import history_views
from st2common.util import isotime
from st2common.util import date as date_utils
from st2api.controllers.v1.actionexecutions import ActionExecutionsController
from st2api.controllers.v1.execution_views import FILTERS_WITH_VALID_NULL_VALUES
from st2common.persistence.execution import ActionExecution
from st2common.models.api.execution import ActionExecutionAPI


class TestActionExecutionFilters(FunctionalTest):

    @classmethod
    def testDownClass(cls):
        pass

    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionFilters, cls).setUpClass()

        cls.dt_base = date_utils.add_utc_tz(datetime.datetime(2014, 12, 25, 0, 0, 0))
        cls.num_records = 100

        cls.refs = {}
        cls.start_timestamps = []
        cls.fake_types = [
            {
                'trigger': copy.deepcopy(fixture.ARTIFACTS['trigger']),
                'trigger_type': copy.deepcopy(fixture.ARTIFACTS['trigger_type']),
                'trigger_instance': copy.deepcopy(fixture.ARTIFACTS['trigger_instance']),
                'rule': copy.deepcopy(fixture.ARTIFACTS['rule']),
                'action': copy.deepcopy(fixture.ARTIFACTS['actions']['chain']),
                'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['action-chain']),
                'liveaction': copy.deepcopy(fixture.ARTIFACTS['liveactions']['workflow']),
                'context': copy.deepcopy(fixture.ARTIFACTS['context']),
                'children': []
            },
            {
                'action': copy.deepcopy(fixture.ARTIFACTS['actions']['local']),
                'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['run-local']),
                'liveaction': copy.deepcopy(fixture.ARTIFACTS['liveactions']['task1'])
            }
        ]

        def assign_parent(child):
            candidates = [v for k, v in cls.refs.items() if v.action['name'] == 'chain']
            if candidates:
                parent = random.choice(candidates)
                child['parent'] = str(parent.id)
                parent.children.append(child['id'])
                cls.refs[str(parent.id)] = ActionExecution.add_or_update(parent)

        for i in range(cls.num_records):
            obj_id = str(bson.ObjectId())
            timestamp = cls.dt_base + datetime.timedelta(seconds=i)
            fake_type = random.choice(cls.fake_types)
            data = copy.deepcopy(fake_type)
            data['id'] = obj_id
            data['start_timestamp'] = isotime.format(timestamp, offset=False)
            data['end_timestamp'] = isotime.format(timestamp, offset=False)
            data['status'] = data['liveaction']['status']
            data['result'] = data['liveaction']['result']
            if fake_type['action']['name'] == 'local' and random.choice([True, False]):
                assign_parent(data)
            wb_obj = ActionExecutionAPI(**data)
            db_obj = ActionExecutionAPI.to_model(wb_obj)
            cls.refs[obj_id] = ActionExecution.add_or_update(db_obj)
            cls.start_timestamps.append(timestamp)

        cls.start_timestamps = sorted(cls.start_timestamps)

    def test_get_all(self):
        response = self.app.get('/v1/executions')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), self.num_records)
        self.assertEqual(response.headers['X-Total-Count'], str(self.num_records))
        ids = [item['id'] for item in response.json]
        self.assertListEqual(sorted(ids), sorted(self.refs.keys()))

    def test_get_all_exclude_attributes(self):
        # No attributes excluded
        response = self.app.get('/v1/executions?action=executions.local&limit=1')

        self.assertEqual(response.status_int, 200)
        self.assertTrue('result' in response.json[0])

        # Exclude "result" attribute
        path = '/v1/executions?action=executions.local&limit=1&exclude_attributes=result'
        response = self.app.get(path)

        self.assertEqual(response.status_int, 200)
        self.assertFalse('result' in response.json[0])

    def test_get_one(self):
        obj_id = random.choice(list(self.refs.keys()))
        response = self.app.get('/v1/executions/%s' % obj_id)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, dict)
        record = response.json
        fake_record = ActionExecutionAPI.from_model(self.refs[obj_id])
        self.assertEqual(record['id'], obj_id)
        self.assertDictEqual(record['action'], fake_record.action)
        self.assertDictEqual(record['runner'], fake_record.runner)
        self.assertDictEqual(record['liveaction'], fake_record.liveaction)

    def test_get_one_failed(self):
        response = self.app.get('/v1/executions/%s' % str(bson.ObjectId()),
                                expect_errors=True)
        self.assertEqual(response.status_int, http_client.NOT_FOUND)

    def test_limit(self):
        limit = 10
        refs = [k for k, v in six.iteritems(self.refs) if v.action['name'] == 'chain']
        response = self.app.get('/v1/executions?action=executions.chain&limit=%s' %
                                limit)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), limit)
        self.assertEqual(response.headers['X-Limit'], str(limit))
        self.assertEqual(response.headers['X-Total-Count'], str(len(refs)), response.json)
        ids = [item['id'] for item in response.json]
        self.assertListEqual(list(set(ids) - set(refs)), [])

    def test_limit_minus_one(self):
        limit = -1
        refs = [k for k, v in six.iteritems(self.refs) if v.action['name'] == 'chain']
        response = self.app.get('/v1/executions?action=executions.chain&limit=%s' % limit)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), len(refs))
        self.assertEqual(response.headers['X-Total-Count'], str(len(refs)), response.json)
        ids = [item['id'] for item in response.json]
        self.assertListEqual(list(set(ids) - set(refs)), [])

    def test_limit_negative(self):
        limit = -22
        response = self.app.get('/v1/executions?action=executions.chain&limit=%s' % limit,
                                expect_errors=True)
        self.assertEqual(response.status_int, 400)
        self.assertEqual(response.json['faultstring'],
                         u'Limit, "-22" specified, must be a positive number.')

    def test_query(self):
        refs = [k for k, v in six.iteritems(self.refs) if v.action['name'] == 'chain']
        response = self.app.get('/v1/executions?action=executions.chain')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), len(refs))
        self.assertEqual(response.headers['X-Total-Count'], str(len(refs)))
        ids = [item['id'] for item in response.json]
        self.assertListEqual(sorted(ids), sorted(refs))

    def test_filters(self):
        excludes = ['parent', 'timestamp', 'action', 'liveaction', 'timestamp_gt',
                    'timestamp_lt', 'status']
        for param, field in six.iteritems(ActionExecutionsController.supported_filters):
            if param in excludes:
                continue

            value = self.fake_types[0]
            for item in field.split('.'):
                value = value[item]
            response = self.app.get('/v1/executions?%s=%s' % (param, value))
            self.assertEqual(response.status_int, 200)
            self.assertIsInstance(response.json, list)
            self.assertGreater(len(response.json), 0)
            self.assertGreater(int(response.headers['X-Total-Count']), 0)

    def test_advanced_filters(self):
        excludes = ['parent', 'timestamp', 'action', 'liveaction', 'timestamp_gt',
                    'timestamp_lt', 'status']
        for param, field in six.iteritems(ActionExecutionsController.supported_filters):
            if param in excludes:
                continue

            value = self.fake_types[0]
            for item in field.split('.'):
                value = value[item]
            response = self.app.get('/v1/executions?filter=%s:%s' % (field, value))
            self.assertEqual(response.status_int, 200)
            self.assertIsInstance(response.json, list)
            self.assertGreater(len(response.json), 0)
            self.assertGreater(int(response.headers['X-Total-Count']), 0)

    def test_advanced_filters_malformed(self):
        response = self.app.get('/v1/executions?filter=a:b,c:d', expect_errors=True)
        self.assertEqual(response.status_int, 400)
        self.assertEqual(response.json, {
            "faultstring": "Cannot resolve field \"a\""
        })
        response = self.app.get('/v1/executions?filter=action.ref', expect_errors=True)
        self.assertEqual(response.status_int, 400)
        self.assertEqual(response.json, {
            "faultstring": "invalid format for filter \"action.ref\""
        })

    def test_parent(self):
        refs = [v for k, v in six.iteritems(self.refs)
                if v.action['name'] == 'chain' and v.children]
        self.assertTrue(refs)
        ref = random.choice(refs)
        response = self.app.get('/v1/executions?parent=%s' % str(ref.id))
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), len(ref.children))
        self.assertEqual(response.headers['X-Total-Count'], str(len(ref.children)))
        ids = [item['id'] for item in response.json]
        self.assertListEqual(sorted(ids), sorted(ref.children))

    def test_parentless(self):
        refs = {k: v for k, v in six.iteritems(self.refs) if not getattr(v, 'parent', None)}
        self.assertTrue(refs)
        self.assertNotEqual(len(refs), self.num_records)
        response = self.app.get('/v1/executions?parent=null')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), len(refs))
        self.assertEqual(response.headers['X-Total-Count'], str(len(refs)))
        ids = [item['id'] for item in response.json]
        self.assertListEqual(sorted(ids), sorted(refs.keys()))

    def test_pagination(self):
        retrieved = []
        page_size = 10
        page_count = int(self.num_records / page_size)
        for i in range(page_count):
            offset = i * page_size
            response = self.app.get('/v1/executions?offset=%s&limit=%s' % (
                offset, page_size))
            self.assertEqual(response.status_int, 200)
            self.assertIsInstance(response.json, list)
            self.assertEqual(len(response.json), page_size)
            self.assertEqual(response.headers['X-Limit'], str(page_size))
            self.assertEqual(response.headers['X-Total-Count'], str(self.num_records))
            ids = [item['id'] for item in response.json]
            self.assertListEqual(list(set(ids) - set(self.refs.keys())), [])
            self.assertListEqual(sorted(list(set(ids) - set(retrieved))), sorted(ids))
            retrieved += ids
        self.assertListEqual(sorted(retrieved), sorted(self.refs.keys()))

    def test_ui_history_query(self):
        # In this test we only care about making sure this exact query works. This query is used
        # by the webui for the history page so it is special and breaking this is bad.
        limit = 50
        history_query = '/v1/executions?limit={}&parent=null&exclude_attributes=' \
                        'result%2Ctrigger_instance&status=&action=&trigger_type=&rule=&' \
                        'offset=0'.format(limit)
        response = self.app.get(history_query)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), limit)
        self.assertTrue(int(response.headers['X-Total-Count']) > limit)

    def test_datetime_range(self):
        dt_range = '2014-12-25T00:00:10Z..2014-12-25T00:00:19Z'
        response = self.app.get('/v1/executions?timestamp=%s' % dt_range)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 10)
        self.assertEqual(response.headers['X-Total-Count'], '10')

        dt1 = response.json[0]['start_timestamp']
        dt2 = response.json[9]['start_timestamp']

        self.assertLess(isotime.parse(dt1), isotime.parse(dt2))

        dt_range = '2014-12-25T00:00:19Z..2014-12-25T00:00:10Z'
        response = self.app.get('/v1/executions?timestamp=%s' % dt_range)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 10)
        self.assertEqual(response.headers['X-Total-Count'], '10')
        dt1 = response.json[0]['start_timestamp']
        dt2 = response.json[9]['start_timestamp']
        self.assertLess(isotime.parse(dt2), isotime.parse(dt1))

    def test_default_sort(self):
        response = self.app.get('/v1/executions')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        dt1 = response.json[0]['start_timestamp']
        dt2 = response.json[len(response.json) - 1]['start_timestamp']
        self.assertLess(isotime.parse(dt2), isotime.parse(dt1))

    def test_ascending_sort(self):
        response = self.app.get('/v1/executions?sort_asc=True')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        dt1 = response.json[0]['start_timestamp']
        dt2 = response.json[len(response.json) - 1]['start_timestamp']
        self.assertLess(isotime.parse(dt1), isotime.parse(dt2))

    def test_descending_sort(self):
        response = self.app.get('/v1/executions?sort_desc=True')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        dt1 = response.json[0]['start_timestamp']
        dt2 = response.json[len(response.json) - 1]['start_timestamp']
        self.assertLess(isotime.parse(dt2), isotime.parse(dt1))

    def test_timestamp_lt_and_gt_filter(self):
        def isoformat(timestamp):
            return isotime.format(timestamp, offset=False)

        index = len(self.start_timestamps) - 1
        timestamp = self.start_timestamps[index]

        # Last (largest) timestamp, there are no executions with a greater timestamp
        timestamp = self.start_timestamps[-1]
        response = self.app.get('/v1/executions?timestamp_gt=%s' % (isoformat(timestamp)))
        self.assertEqual(len(response.json), 0)

        # First (smallest) timestamp, there are no executions with a smaller timestamp
        timestamp = self.start_timestamps[0]
        response = self.app.get('/v1/executions?timestamp_lt=%s' % (isoformat(timestamp)))
        self.assertEqual(len(response.json), 0)

        # Second last, there should be one timestamp greater than it
        timestamp = self.start_timestamps[-2]
        response = self.app.get('/v1/executions?timestamp_gt=%s' % (isoformat(timestamp)))
        self.assertEqual(len(response.json), 1)
        self.assertTrue(isotime.parse(response.json[0]['start_timestamp']) > timestamp)

        # Second one, there should be one timestamp smaller than it
        timestamp = self.start_timestamps[1]
        response = self.app.get('/v1/executions?timestamp_lt=%s' % (isoformat(timestamp)))
        self.assertEqual(len(response.json), 1)
        self.assertTrue(isotime.parse(response.json[0]['start_timestamp']) < timestamp)

        # Half of the timestamps should be smaller
        index = (len(self.start_timestamps) - 1) // 2
        timestamp = self.start_timestamps[index]
        response = self.app.get('/v1/executions?timestamp_lt=%s' % (isoformat(timestamp)))
        self.assertEqual(len(response.json), index)
        self.assertTrue(isotime.parse(response.json[0]['start_timestamp']) < timestamp)

        # Half of the timestamps should be greater
        index = (len(self.start_timestamps) - 1) // 2
        timestamp = self.start_timestamps[-index]
        response = self.app.get('/v1/executions?timestamp_gt=%s' % (isoformat(timestamp)))
        self.assertEqual(len(response.json), (index - 1))
        self.assertTrue(isotime.parse(response.json[0]['start_timestamp']) > timestamp)

        # Both, lt and gt filters, should return exactly two results
        timestamp_gt = self.start_timestamps[10]
        timestamp_lt = self.start_timestamps[13]
        response = self.app.get('/v1/executions?timestamp_gt=%s&timestamp_lt=%s' %
                                (isoformat(timestamp_gt), isoformat(timestamp_lt)))
        self.assertEqual(len(response.json), 2)
        self.assertTrue(isotime.parse(response.json[0]['start_timestamp']) > timestamp_gt)
        self.assertTrue(isotime.parse(response.json[1]['start_timestamp']) > timestamp_gt)
        self.assertTrue(isotime.parse(response.json[0]['start_timestamp']) < timestamp_lt)
        self.assertTrue(isotime.parse(response.json[1]['start_timestamp']) < timestamp_lt)

    def test_filters_view(self):
        response = self.app.get('/v1/executions/views/filters')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, dict)
        self.assertEqual(len(response.json), len(history_views.ARTIFACTS['filters']['default']))
        for key, value in six.iteritems(history_views.ARTIFACTS['filters']['default']):
            filter_values = response.json[key]

            # Verify empty (None / null) filters are excluded
            if key not in FILTERS_WITH_VALID_NULL_VALUES:
                self.assertTrue(None not in filter_values)

            if None in value or None in filter_values:
                filter_values = [item for item in filter_values if item is not None]
                value = [item for item in value if item is not None]

            self.assertEqual(set(filter_values), set(value))

    def test_filters_view_specific_types(self):
        response = self.app.get('/v1/executions/views/filters?types=action,user,nonexistent')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, dict)
        self.assertEqual(len(response.json), len(history_views.ARTIFACTS['filters']['specific']))
        for key, value in six.iteritems(history_views.ARTIFACTS['filters']['specific']):
            self.assertEqual(set(response.json[key]), set(value))
