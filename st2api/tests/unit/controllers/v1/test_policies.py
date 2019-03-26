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

import mock
import six
from six.moves import http_client

from st2common.models.api.policy import PolicyTypeAPI, PolicyAPI
from st2common.persistence.policy import PolicyType, Policy
from st2common.transport.publishers import PoolPublisher
from st2api.controllers.v1.policies import PolicyTypeController
from st2api.controllers.v1.policies import PolicyController
from st2tests.fixturesloader import FixturesLoader

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

__all__ = [
    'PolicyTypeControllerTestCase',
    'PolicyControllerTestCase'
]


TEST_FIXTURES = {
    'policytypes': [
        'fake_policy_type_1.yaml',
        'fake_policy_type_2.yaml'
    ],
    'policies': [
        'policy_1.yaml',
        'policy_2.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)


class PolicyTypeControllerTestCase(FunctionalTest,
                               APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/policytypes'
    controller_cls = PolicyTypeController
    include_attribute_field_name = 'module'
    exclude_attribute_field_name = 'parameters'

    base_url = '/v1/policytypes'

    @classmethod
    def setUpClass(cls):
        super(PolicyTypeControllerTestCase, cls).setUpClass()

        cls.policy_type_dbs = []

        for _, fixture in six.iteritems(FIXTURES['policytypes']):
            instance = PolicyTypeAPI(**fixture)
            policy_type_db = PolicyType.add_or_update(PolicyTypeAPI.to_model(instance))
            cls.policy_type_dbs.append(policy_type_db)

    def test_policy_type_get_all(self):
        resp = self.__do_get_all()
        self.assertEqual(resp.status_int, 200)
        self.assertGreater(len(resp.json), 0)

    def test_policy_type_filter(self):
        resp = self.__do_get_all()
        self.assertEqual(resp.status_int, 200)
        self.assertGreater(len(resp.json), 0)
        selected = resp.json[0]

        resp = self.__do_get_all(filter='resource_type=%s&name=%s' %
                                 (selected['resource_type'], selected['name']))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(self.__get_obj_id(resp, idx=0), selected['id'])

        resp = self.__do_get_all(filter='name=%s' % selected['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(self.__get_obj_id(resp, idx=0), selected['id'])

        resp = self.__do_get_all(filter='resource_type=%s' % selected['resource_type'])
        self.assertEqual(resp.status_int, 200)
        self.assertGreater(len(resp.json), 1)

    def test_policy_type_filter_empty(self):
        resp = self.__do_get_all(filter='resource_type=yo&name=whatever')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 0)

    def test_policy_type_get_one(self):
        resp = self.__do_get_all()
        self.assertEqual(resp.status_int, 200)
        self.assertGreater(len(resp.json), 0)
        selected = resp.json[0]

        resp = self.__do_get_one(selected['id'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(self.__get_obj_id(resp), selected['id'])

        resp = self.__do_get_one(selected['ref'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(self.__get_obj_id(resp), selected['id'])

    def test_policy_type_get_one_fail(self):
        resp = self.__do_get_one('1')
        self.assertEqual(resp.status_int, 404)

    def _insert_mock_models(self):
        result = []
        for policy_type_db in self.policy_type_dbs:
            result.append(policy_type_db.id)

        return result

    def _delete_mock_models(self, object_ids):
        pass

    @staticmethod
    def __get_obj_id(resp, idx=-1):
        return resp.json['id'] if idx < 0 else resp.json[idx]['id']

    def __do_get_all(self, filter=None):
        url = '%s?%s' % (self.base_url, filter) if filter else self.base_url
        return self.app.get(url, expect_errors=True)

    def __do_get_one(self, id):
        return self.app.get('%s/%s' % (self.base_url, id), expect_errors=True)


class PolicyControllerTestCase(FunctionalTest,
                               APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/policies'
    controller_cls = PolicyController
    include_attribute_field_name = 'policy_type'
    exclude_attribute_field_name = 'parameters'

    base_url = '/v1/policies'

    @classmethod
    def setUpClass(cls):
        super(PolicyControllerTestCase, cls).setUpClass()

        for _, fixture in six.iteritems(FIXTURES['policytypes']):
            instance = PolicyTypeAPI(**fixture)
            PolicyType.add_or_update(PolicyTypeAPI.to_model(instance))

        cls.policy_dbs = []

        for _, fixture in six.iteritems(FIXTURES['policies']):
            instance = PolicyAPI(**fixture)
            policy_db = Policy.add_or_update(PolicyAPI.to_model(instance))
            cls.policy_dbs.append(policy_db)

    def test_get_all(self):
        resp = self.__do_get_all()
        self.assertEqual(resp.status_int, 200)
        self.assertGreater(len(resp.json), 0)

    def test_filter(self):
        resp = self.__do_get_all()
        self.assertEqual(resp.status_int, 200)
        self.assertGreater(len(resp.json), 0)
        selected = resp.json[0]

        resp = self.__do_get_all(filter='pack=%s&name=%s' % (selected['pack'], selected['name']))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(self.__get_obj_id(resp, idx=0), selected['id'])

        resp = self.__do_get_all(filter='name=%s' % selected['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(self.__get_obj_id(resp, idx=0), selected['id'])

        resp = self.__do_get_all(filter='pack=%s' % selected['pack'])
        self.assertEqual(resp.status_int, 200)
        self.assertGreater(len(resp.json), 1)

    def test_filter_empty(self):
        resp = self.__do_get_all(filter='pack=yo&name=whatever')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 0)

    def test_get_one(self):
        resp = self.__do_get_all()
        self.assertEqual(resp.status_int, 200)
        self.assertGreater(len(resp.json), 0)
        selected = resp.json[0]

        resp = self.__do_get_one(selected['id'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(self.__get_obj_id(resp), selected['id'])

        resp = self.__do_get_one(selected['ref'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(self.__get_obj_id(resp), selected['id'])

    def test_get_one_fail(self):
        resp = self.__do_get_one('1')
        self.assertEqual(resp.status_int, 404)

    def test_crud(self):
        instance = self.__create_instance()

        post_resp = self.__do_post(instance)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        get_resp = self.__do_get_one(self.__get_obj_id(post_resp))
        self.assertEqual(get_resp.status_int, http_client.OK)

        updated_input = get_resp.json
        updated_input['enabled'] = not updated_input['enabled']
        put_resp = self.__do_put(self.__get_obj_id(post_resp), updated_input)
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.assertEqual(put_resp.json['enabled'], updated_input['enabled'])

        del_resp = self.__do_delete(self.__get_obj_id(post_resp))
        self.assertEqual(del_resp.status_int, http_client.NO_CONTENT)

    def test_post_duplicate(self):
        instance = self.__create_instance()

        post_resp = self.__do_post(instance)
        self.assertEqual(post_resp.status_int, http_client.CREATED)

        post_dup_resp = self.__do_post(instance)
        self.assertEqual(post_dup_resp.status_int, http_client.CONFLICT)

        del_resp = self.__do_delete(self.__get_obj_id(post_resp))
        self.assertEqual(del_resp.status_int, http_client.NO_CONTENT)

    def test_put_not_found(self):
        updated_input = self.__create_instance()
        put_resp = self.__do_put('12345', updated_input)
        self.assertEqual(put_resp.status_int, http_client.NOT_FOUND)

    def test_put_sys_pack(self):
        instance = self.__create_instance()
        instance['pack'] = 'core'

        post_resp = self.__do_post(instance)
        self.assertEqual(post_resp.status_int, http_client.CREATED)

        updated_input = post_resp.json
        updated_input['enabled'] = not updated_input['enabled']
        put_resp = self.__do_put(self.__get_obj_id(post_resp), updated_input)
        self.assertEqual(put_resp.status_int, http_client.BAD_REQUEST)
        self.assertEqual(put_resp.json['faultstring'],
                         "Resources belonging to system level packs can't be manipulated")

        # Clean up manually since API won't delete object in sys pack.
        Policy.delete(Policy.get_by_id(self.__get_obj_id(post_resp)))

    def test_delete_not_found(self):
        del_resp = self.__do_delete('12345')
        self.assertEqual(del_resp.status_int, http_client.NOT_FOUND)

    def test_delete_sys_pack(self):
        instance = self.__create_instance()
        instance['pack'] = 'core'

        post_resp = self.__do_post(instance)
        self.assertEqual(post_resp.status_int, http_client.CREATED)

        del_resp = self.__do_delete(self.__get_obj_id(post_resp))
        self.assertEqual(del_resp.status_int, http_client.BAD_REQUEST)
        self.assertEqual(del_resp.json['faultstring'],
                         "Resources belonging to system level packs can't be manipulated")

        # Clean up manually since API won't delete object in sys pack.
        Policy.delete(Policy.get_by_id(self.__get_obj_id(post_resp)))

    def _insert_mock_models(self):
        result = []
        for policy_db in self.policy_dbs:
            result.append(policy_db.id)

        return result

    def _delete_mock_models(self, object_ids):
        pass

    @staticmethod
    def __create_instance():
        return {
            'name': 'myaction.mypolicy',
            'pack': 'mypack',
            'resource_ref': 'mypack.myaction',
            'policy_type': 'action.mock_policy_error',
            'parameters': {
                'k1': 'v1'
            }
        }

    @staticmethod
    def __get_obj_id(resp, idx=-1):
        return resp.json['id'] if idx < 0 else resp.json[idx]['id']

    def __do_get_all(self, filter=None):
        url = '%s?%s' % (self.base_url, filter) if filter else self.base_url
        return self.app.get(url, expect_errors=True)

    def __do_get_one(self, id):
        return self.app.get('%s/%s' % (self.base_url, id), expect_errors=True)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def __do_post(self, instance):
        return self.app.post_json(self.base_url, instance, expect_errors=True)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def __do_put(self, id, instance):
        return self.app.put_json('%s/%s' % (self.base_url, id), instance, expect_errors=True)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def __do_delete(self, id):
        return self.app.delete('%s/%s' % (self.base_url, id), expect_errors=True)
