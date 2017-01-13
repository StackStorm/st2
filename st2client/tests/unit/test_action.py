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

import json
import mock
import logging

from tests import base

from st2client import shell
from st2client import models
from st2client.utils import httpclient

LOG = logging.getLogger(__name__)

RUNNER1 = {
    "enabled": True,
    "runner_parameters": {
        "bool": {"type": "boolean"},
        "int": {"type": "integer"},
        "float": {"type": "number"},
        "json": {"type": "object"},
        "list": {"type": "array"},
        "str": {"type": "string"}
    },
    "name": "mock-runner1"
}

ACTION1 = {
    "ref": "mockety.mock1",
    "runner_type": "mock-runner1",
    "name": "mock1",
    "parameters": {},
    "enabled": True,
    "entry_point": "",
    "pack": "mockety"
}

RUNNER2 = {
    "enabled": True,
    "runner_parameters": {},
    "name": "mock-runner2"
}

ACTION2 = {
    "ref": "mockety.mock2",
    "runner_type": "mock-runner2",
    "name": "mock2",
    "parameters": {
        "bool": {"type": "boolean"},
        "int": {"type": "integer"},
        "float": {"type": "number"},
        "json": {"type": "object"},
        "list": {"type": "array"},
        "str": {"type": "string"}
    },
    "enabled": True,
    "entry_point": "",
    "pack": "mockety"
}

LIVE_ACTION = {
    'action': 'mockety.mock',
    'status': 'complete',
    'result': 'non-empty'
}


def get_by_name(name, **kwargs):
    if name == 'mock-runner1':
        return models.RunnerType(**RUNNER1)
    if name == 'mock-runner2':
        return models.RunnerType(**RUNNER2)


def get_by_ref(**kwargs):
    ref = kwargs.get('ref_or_id', None)

    if not ref:
        raise Exception('Actions must be referred to by "ref".')

    if ref == 'mockety.mock1':
        return models.Action(**ACTION1)
    if ref == 'mockety.mock2':
        return models.Action(**ACTION2)


class ActionCommandTestCase(base.BaseCLITestCase):

    def __init__(self, *args, **kwargs):
        super(ActionCommandTestCase, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_runner_param_bool_conversion(self):
        self.shell.run(['run', 'mockety.mock1', 'bool=false'])
        expected = {'action': 'mockety.mock1', 'user': None, 'parameters': {'bool': False}}
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_runner_param_integer_conversion(self):
        self.shell.run(['run', 'mockety.mock1', 'int=30'])
        expected = {'action': 'mockety.mock1', 'user': None, 'parameters': {'int': 30}}
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_runner_param_float_conversion(self):
        self.shell.run(['run', 'mockety.mock1', 'float=3.01'])
        expected = {'action': 'mockety.mock1', 'user': None, 'parameters': {'float': 3.01}}
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_runner_param_json_conversion(self):
        self.shell.run(['run', 'mockety.mock1', 'json={"a":1}'])
        expected = {'action': 'mockety.mock1', 'user': None, 'parameters': {'json': {'a': 1}}}
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_runner_param_array_conversion(self):
        self.shell.run(['run', 'mockety.mock1', 'list=one,two,three'])
        expected = {
            'action': 'mockety.mock1',
            'user': None,
            'parameters': {
                'list': [
                    'one',
                    'two',
                    'three'
                ]
            }
        }
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_runner_param_array_object_conversion(self):
        self.shell.run(
            [
                'run',
                'mockety.mock1',
                'list=[{"foo":1, "ponies":"rainbows"},{"pluto":false, "earth":true}]'
            ]
        )
        expected = {
            'action': 'mockety.mock1',
            'user': None,
            'parameters': {
                'list': [
                    {
                        'foo': 1,
                        'ponies': 'rainbows'
                    },
                    {
                        'pluto': False,
                        'earth': True
                    }
                ]
            }
        }
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_param_bool_conversion(self):
        self.shell.run(['run', 'mockety.mock2', 'bool=false'])
        expected = {'action': 'mockety.mock2', 'user': None, 'parameters': {'bool': False}}
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_param_integer_conversion(self):
        self.shell.run(['run', 'mockety.mock2', 'int=30'])
        expected = {'action': 'mockety.mock2', 'user': None, 'parameters': {'int': 30}}
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_param_float_conversion(self):
        self.shell.run(['run', 'mockety.mock2', 'float=3.01'])
        expected = {'action': 'mockety.mock2', 'user': None, 'parameters': {'float': 3.01}}
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_param_json_conversion(self):
        self.shell.run(['run', 'mockety.mock2', 'json={"a":1}'])
        expected = {'action': 'mockety.mock2', 'user': None, 'parameters': {'json': {'a': 1}}}
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_param_array_conversion(self):
        self.shell.run(['run', 'mockety.mock2', 'list=one,two,three'])
        expected = {
            'action': 'mockety.mock2',
            'user': None,
            'parameters': {
                'list': [
                    'one',
                    'two',
                    'three'
                ]
            }
        }
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_param_array_conversion_single_element_str(self):
        self.shell.run(['run', 'mockety.mock2', 'list=one'])
        expected = {
            'action': 'mockety.mock2',
            'user': None,
            'parameters': {
                'list': [
                    'one'
                ]
            }
        }
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_param_array_conversion_single_element_int(self):
        self.shell.run(['run', 'mockety.mock2', 'list=1'])
        expected = {
            'action': 'mockety.mock2',
            'user': None,
            'parameters': {
                'list': [
                    1
                ]
            }
        }
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_param_array_object_conversion(self):
        self.shell.run(
            [
                'run',
                'mockety.mock2',
                'list=[{"foo":1, "ponies":"rainbows"},{"pluto":false, "earth":true}]'
            ]
        )
        expected = {
            'action': 'mockety.mock2',
            'user': None,
            'parameters': {
                'list': [
                    {
                        'foo': 1,
                        'ponies': 'rainbows'
                    },
                    {
                        'pluto': False,
                        'earth': True
                    }
                ]
            }
        }
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_param_value_with_equal_sign(self):
        self.shell.run(['run', 'mockety.mock2', 'key=foo=bar&ponies=unicorns'])
        expected = {'action': 'mockety.mock2', 'user': None,
                    'parameters': {'key': 'foo=bar&ponies=unicorns'}}
        httpclient.HTTPClient.post.assert_called_with('/executions', expected)
