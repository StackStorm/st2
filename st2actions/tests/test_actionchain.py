import tests.config
tests.config.parse_args()

import json
import mock
import os
import six

from unittest2 import TestCase

from st2actions.runners import actionchainrunner as acr
from st2actions.container.service import RunnerContainerService
from st2client.models import ResourceManager
from st2common.exceptions import actionrunner as runnerexceptions
from st2common.models.api import action

CHAIN_1_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources/chain1.json')
MALFORMED_CHAIN_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'resources/malformedchain.json')

with open(CHAIN_1_PATH, 'r') as fd:
    CHAIN_1 = json.load(fd)

CHAIN_EMPTY = {}


class DummyActionExecution(object):

    def __init__(self, status=action.ACTIONEXEC_STATUS_COMPLETE, result=''):
        self.id = None
        self.status = status
        self.result = result


class DummyAction(object):

    def __init__(self):
        self.content_pack = None
        self.entry_point = None


class TestActionChain(TestCase):

    def test_chain_creation_basic(self):
        action_chain = acr.ActionChain(CHAIN_1)

        expected_node_count = 0
        expected_link_count = 0
        for node in CHAIN_1['chain']:
            expected_node_count += 1
            if 'on-success' in node:
                expected_link_count += 1
            if 'on-failure' in node:
                expected_link_count += 1

        self.assertEquals(len(action_chain.nodes), expected_node_count)

        link_count = 0
        for _, links in six.iteritems(action_chain.links):
            link_count += len(links)
        self.assertEquals(link_count, expected_link_count)

        self.assertEquals(action_chain.default, CHAIN_1['default'])

    def test_chain_iteration(self):
        action_chain = acr.ActionChain(CHAIN_1)

        for node in CHAIN_1['chain']:
            if 'on-success' in node:
                next_node = action_chain.get_next_node(node['name'], 'on-success')
                self.assertEquals(next_node.name, node['on-success'])
            if 'on-failure' in node:
                next_node = action_chain.get_next_node(node['name'], 'on-failure')
                self.assertEquals(next_node.name, node['on-failure'])

        default = action_chain.get_next_node()
        self.assertEquals(type(default), acr.ActionChain.Node)
        self.assertEquals(default.name, CHAIN_1['default'])

    def test_empty_chain(self):
        action_chain = acr.ActionChain(CHAIN_EMPTY)
        self.assertEquals(len(action_chain.nodes), 0)
        self.assertEquals(len(action_chain.links), 0)
        self.assertEquals(action_chain.default, '')


class TestActionChainRunner(TestCase):

    def test_runner_creation(self):
        runner = acr.get_runner()
        self.assertTrue(runner)
        self.assertTrue(runner.id)

    @mock.patch.object(RunnerContainerService, 'get_entry_point_abs_path', mock.MagicMock(
        return_value=MALFORMED_CHAIN_PATH))
    def test_malformed_chain(self):
        try:
            chain_runner = acr.get_runner()
            chain_runner.entry_point = ''
            chain_runner.action = DummyAction()
            chain_runner.container_service = RunnerContainerService(None)
            chain_runner.pre_run()
            self.assertTrue(False, 'Expected pre_run to fail.')
        except runnerexceptions.ActionRunnerPreRunError:
            self.assertTrue(True)

    @mock.patch.object(RunnerContainerService, 'get_entry_point_abs_path', mock.MagicMock(
        return_value=CHAIN_1_PATH))
    @mock.patch.object(ResourceManager, 'create',
        return_value=DummyActionExecution())
    def test_chain_runner_success_path(self, resourcemgr_create):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = ''
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService(None)
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEquals(resourcemgr_create.call_count, 3)

    @mock.patch.object(RunnerContainerService, 'get_entry_point_abs_path', mock.MagicMock(
        return_value=CHAIN_1_PATH))
    @mock.patch('eventlet.sleep', mock.MagicMock())
    @mock.patch.object(ResourceManager, 'get_by_id', mock.MagicMock(
        return_value=DummyActionExecution()))
    @mock.patch.object(ResourceManager, 'create',
        return_value=DummyActionExecution(status=action.ACTIONEXEC_STATUS_RUNNING))
    def test_chain_runner_success_path_with_wait(self, resourcemgr_create):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = ''
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService(None)
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEquals(resourcemgr_create.call_count, 3)

    @mock.patch.object(RunnerContainerService, 'get_entry_point_abs_path', mock.MagicMock(
        return_value=CHAIN_1_PATH))
    @mock.patch.object(ResourceManager, 'create',
        return_value=DummyActionExecution(status=action.ACTIONEXEC_STATUS_ERROR))
    def test_chain_runner_failure_path(self, resourcemgr_create):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = ''
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService(None)
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 2. Not great but works.
        self.assertEquals(resourcemgr_create.call_count, 2)

    @mock.patch.object(RunnerContainerService, 'get_entry_point_abs_path', mock.MagicMock(
        return_value=CHAIN_1_PATH))
    @mock.patch.object(ResourceManager, 'create', side_effect=RuntimeError('Test Failure.'))
    def test_chain_runner_action_exception(self, resourcemgr_create):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = ''
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService(None)
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 2. Not great but works.
        self.assertEquals(resourcemgr_create.call_count, 2)
