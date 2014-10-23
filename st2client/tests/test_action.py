import os
import sys
import json
import mock
import logging
import unittest2

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
        "str": {"type": "string"}
    },
    "name": "mock-runner1"
}

ACTION1 = {
    "runner_type": "mock-runner1",
    "name": "mock1",
    "parameters": {},
    "required_parameters": [],
    "enabled": True,
    "entry_point": ""
}

RUNNER2 = {
    "enabled": True,
    "runner_parameters": {},
    "name": "mock-runner2"
}

ACTION2 = {
    "runner_type": "mock-runner2",
    "name": "mock2",
    "parameters": {
        "bool": {"type": "boolean"},
        "int": {"type": "integer"},
        "float": {"type": "number"},
        "json": {"type": "object"},
        "str": {"type": "string"}
    },
    "required_parameters": [],
    "enabled": True,
    "entry_point": ""
}

ACTION_EXECUTION = {
    'action': {'name': 'mock'},
    'status': 'complete'
}


def get_by_name(name, **kwargs):
    if name == 'mock-runner1':
        return models.RunnerType(**RUNNER1)
    if name == 'mock1':
        return models.Action(**ACTION1)
    if name == 'mock-runner2':
        return models.RunnerType(**RUNNER2)
    if name == 'mock2':
        return models.Action(**ACTION2)


class ActionCommandTestCase(unittest2.TestCase):

    def __init__(self, *args, **kwargs):
        super(ActionCommandTestCase, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()

    def setUp(self):
        # Redirect standard output and error to null. If not, then
        # some of the print output from shell commands will pollute
        # the test output.
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    def tearDown(self):
        # Reset to original stdout and stderr.
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ACTION_EXECUTION), 200, 'OK')))
    def test_runner_param_bool_conversion(self):
        self.shell.run(['run', 'mock1', 'bool=false'])
        expected = {'action': {'name': 'mock1'}, 'parameters': {'bool': False}}
        httpclient.HTTPClient.post.assert_called_with('/actionexecutions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ACTION_EXECUTION), 200, 'OK')))
    def test_runner_param_integer_conversion(self):
        self.shell.run(['run', 'mock1', 'int=30'])
        expected = {'action': {'name': 'mock1'}, 'parameters': {'int': 30}}
        httpclient.HTTPClient.post.assert_called_with('/actionexecutions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ACTION_EXECUTION), 200, 'OK')))
    def test_runner_param_float_conversion(self):
        self.shell.run(['run', 'mock1', 'float=3.01'])
        expected = {'action': {'name': 'mock1'}, 'parameters': {'float': 3.01}}
        httpclient.HTTPClient.post.assert_called_with('/actionexecutions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ACTION_EXECUTION), 200, 'OK')))
    def test_runner_param_json_conversion(self):
        self.shell.run(['run', 'mock1', 'json={"a":1}'])
        expected = {'action': {'name': 'mock1'}, 'parameters': {'json': {'a': 1}}}
        httpclient.HTTPClient.post.assert_called_with('/actionexecutions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ACTION_EXECUTION), 200, 'OK')))
    def test_param_bool_conversion(self):
        self.shell.run(['run', 'mock2', 'bool=false'])
        expected = {'action': {'name': 'mock2'}, 'parameters': {'bool': False}}
        httpclient.HTTPClient.post.assert_called_with('/actionexecutions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ACTION_EXECUTION), 200, 'OK')))
    def test_param_integer_conversion(self):
        self.shell.run(['run', 'mock2', 'int=30'])
        expected = {'action': {'name': 'mock2'}, 'parameters': {'int': 30}}
        httpclient.HTTPClient.post.assert_called_with('/actionexecutions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ACTION_EXECUTION), 200, 'OK')))
    def test_param_float_conversion(self):
        self.shell.run(['run', 'mock2', 'float=3.01'])
        expected = {'action': {'name': 'mock2'}, 'parameters': {'float': 3.01}}
        httpclient.HTTPClient.post.assert_called_with('/actionexecutions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ACTION_EXECUTION), 200, 'OK')))
    def test_param_json_conversion(self):
        self.shell.run(['run', 'mock2', 'json={"a":1}'])
        expected = {'action': {'name': 'mock2'}, 'parameters': {'json': {'a': 1}}}
        httpclient.HTTPClient.post.assert_called_with('/actionexecutions', expected)

    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(side_effect=get_by_name))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ACTION_EXECUTION), 200, 'OK')))
    def test_param_value_with_equal_sign(self):
        self.shell.run(['run', 'mock2', 'key=foo=bar&ponies=unicorns'])
        expected = {'action': {'name': 'mock2'},
                    'parameters': {'key': 'foo=bar&ponies=unicorns'}}
        httpclient.HTTPClient.post.assert_called_with('/actionexecutions', expected)
