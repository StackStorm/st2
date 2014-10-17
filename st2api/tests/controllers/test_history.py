import copy
import random
import datetime

import bson
import six
from six.moves import http_client

from tests import FunctionalTest
from tests.fixtures import history as fixture
from st2common.util import isotime
from st2api.controllers.history import ActionExecutionController
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI


class TestActionExecutionHistory(FunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionHistory, cls).setUpClass()

        cls.dt_base = isotime.add_utc_tz(datetime.datetime(2014, 12, 25, 0, 0, 0))
        cls.num_records = 100
        cls.refs = {}

        cls.fake_types = [
            {
                'trigger': copy.deepcopy(fixture.ARTIFACTS['trigger']),
                'trigger_type': copy.deepcopy(fixture.ARTIFACTS['trigger_type']),
                'trigger_instance': copy.deepcopy(fixture.ARTIFACTS['trigger_instance']),
                'rule': copy.deepcopy(fixture.ARTIFACTS['rule']),
                'action': copy.deepcopy(fixture.ARTIFACTS['actions']['chain']),
                'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['action-chain']),
                'execution': copy.deepcopy(fixture.ARTIFACTS['executions']['workflow']),
                'children': []
            },
            {
                'action': copy.deepcopy(fixture.ARTIFACTS['actions']['local']),
                'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['run-local']),
                'execution': copy.deepcopy(fixture.ARTIFACTS['executions']['task1'])
            }
        ]

        def assign_parent(child):
            candidates = [v for k, v in cls.refs.iteritems() if v.action['name'] == 'chain']
            if candidates:
                parent = random.choice(candidates)
                child['parent'] = str(parent.id)
                parent.children.append(child['id'])
                cls.refs[str(parent.id)] = ActionExecutionHistory.add_or_update(parent)

        for i in range(cls.num_records):
            obj_id = str(bson.ObjectId())
            timestamp = cls.dt_base + datetime.timedelta(seconds=i)
            fake_type = random.choice(cls.fake_types)
            data = copy.deepcopy(fake_type)
            data['id'] = obj_id
            data['execution']['start_timestamp'] = isotime.format(timestamp, offset=False)
            if fake_type['action']['name'] == 'local' and random.choice([True, False]):
                assign_parent(data)
            wb_obj = ActionExecutionHistoryAPI(**data)
            db_obj = ActionExecutionHistoryAPI.to_model(wb_obj)
            cls.refs[obj_id] = ActionExecutionHistory.add_or_update(db_obj)

    def test_get_all(self):
        response = self.app.get('/history/executions')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), self.num_records)
        ids = [item['id'] for item in response.json]
        self.assertListEqual(sorted(ids), sorted(self.refs.keys()))

    def test_get_one(self):
        obj_id = random.choice(self.refs.keys())
        response = self.app.get('/history/executions/%s' % obj_id)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, dict)
        record = response.json
        fake_record = ActionExecutionHistoryAPI.from_model(self.refs[obj_id])
        self.assertEqual(record['id'], obj_id)
        self.assertDictEqual(record['action'], fake_record.action)
        self.assertDictEqual(record['runner'], fake_record.runner)
        self.assertDictEqual(record['execution'], fake_record.execution)

    def test_get_one_failed(self):
        response = self.app.get('/history/executions/%s' % str(bson.ObjectId()), expect_errors=True)
        self.assertEqual(response.status_int, http_client.NOT_FOUND)

    def test_limit(self):
        limit = 10
        refs = [k for k, v in six.iteritems(self.refs) if v.action['name'] == 'chain']
        response = self.app.get('/history/executions?action_name=chain&action_pack=core&limit=%s' %
                                limit)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), limit)
        ids = [item['id'] for item in response.json]
        self.assertListEqual(list(set(ids) - set(refs)), [])

    def test_query(self):
        refs = [k for k, v in six.iteritems(self.refs) if v.action['name'] == 'chain']
        response = self.app.get('/history/executions?action_name=chain&action_pack=core')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), len(refs))
        ids = [item['id'] for item in response.json]
        self.assertListEqual(sorted(ids), sorted(refs))

    def test_filters(self):
        excludes = ['parent', 'timestamp']
        for param, field in six.iteritems(ActionExecutionController.supported_filters):
            if param in excludes:
                continue
            value = self.fake_types[0]
            for item in field.split('__'):
                value = value[item]
            response = self.app.get('/history/executions?%s=%s' % (param, value))
            self.assertEqual(response.status_int, 200)
            self.assertIsInstance(response.json, list)
            self.assertGreater(len(response.json), 0)

    def test_parent(self):
        refs = [v for k, v in six.iteritems(self.refs)
                if v.action['name'] == 'chain' and v.children]
        self.assertTrue(refs)
        ref = random.choice(refs)
        response = self.app.get('/history/executions?parent=%s' % str(ref.id))
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), len(ref.children))
        ids = [item['id'] for item in response.json]
        self.assertListEqual(sorted(ids), sorted(ref.children))

    def test_parentless(self):
        refs = {k: v for k, v in six.iteritems(self.refs) if not getattr(v, 'parent', None)}
        self.assertTrue(refs)
        self.assertNotEqual(len(refs), self.num_records)
        response = self.app.get('/history/executions?parent=null')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), len(refs))
        ids = [item['id'] for item in response.json]
        self.assertListEqual(sorted(ids), sorted(refs.keys()))

    def test_pagination(self):
        retrieved = []
        page_size = 10
        page_count = self.num_records / page_size
        for i in range(page_count):
            offset = i * page_size
            response = self.app.get('/history/executions?offset=%s&limit=%s' % (offset, page_size))
            self.assertEqual(response.status_int, 200)
            self.assertIsInstance(response.json, list)
            self.assertEqual(len(response.json), page_size)
            ids = [item['id'] for item in response.json]
            self.assertListEqual(list(set(ids) - set(self.refs.keys())), [])
            self.assertListEqual(sorted(list(set(ids) - set(retrieved))), sorted(ids))
            retrieved += ids
        self.assertListEqual(sorted(retrieved), sorted(self.refs.keys()))

    def test_datetime_range(self):
        dt_range = '2014-12-25T00:00:10Z..2014-12-25T00:00:19Z'
        response = self.app.get('/history/executions?timestamp=%s' % dt_range)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 10)
        dt1 = response.json[0]['execution']['start_timestamp']
        dt2 = response.json[9]['execution']['start_timestamp']
        self.assertLess(isotime.parse(dt1), isotime.parse(dt2))

        dt_range = '2014-12-25T00:00:19Z..2014-12-25T00:00:10Z'
        response = self.app.get('/history/executions?timestamp=%s' % dt_range)
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 10)
        dt1 = response.json[0]['execution']['start_timestamp']
        dt2 = response.json[9]['execution']['start_timestamp']
        self.assertLess(isotime.parse(dt2), isotime.parse(dt1))

    def test_default_sort(self):
        response = self.app.get('/history/executions')
        self.assertEqual(response.status_int, 200)
        self.assertIsInstance(response.json, list)
        dt1 = response.json[0]['execution']['start_timestamp']
        dt2 = response.json[len(response.json) - 1]['execution']['start_timestamp']
        self.assertLess(isotime.parse(dt2), isotime.parse(dt1))
