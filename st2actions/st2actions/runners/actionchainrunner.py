import eventlet
import jinja2
import json
import six
import uuid

from oslo.config import cfg

from st2actions.runners import ActionRunner
from st2client import models
from st2client.client import Client
from st2common import log as logging
from st2common.exceptions import actionrunner as runnerexceptions
from st2common.models.api.action import ACTIONEXEC_STATUS_ERROR, ACTIONEXEC_STATUS_COMPLETE

LOG = logging.getLogger(__name__)


class ActionChain(object):

    class Node(object):

        def __init__(self, name, action_name, params):
            self.name = name
            self.action_name = action_name
            self.params = params

    class Link(object):

        def __init__(self, head, tail, condition):
            self.head = head
            self.tail = tail
            self.condition = condition

    def __init__(self, chainspec):
        chain = chainspec.get('chain', [])
        self.default = chainspec.get('default', '')
        self.nodes = {}
        self.links = {}
        for node in chain:
            node_name = node['name']
            self.nodes[node_name] = ActionChain.Node(
                node_name, node['action'], node['params'])
            self.links[node_name] = []
            on_success = node.get('on-success', None)
            if on_success:
                self.links[node_name].append(ActionChain.Link(node_name, on_success, 'on-success'))
            on_failure = node.get('on-failure', None)
            if on_failure:
                self.links[node_name].append(ActionChain.Link(node_name, on_failure, 'on-failure'))

    def get_next_node(self, curr_node_name=None, condition='on-success'):
        if not curr_node_name:
            return self.nodes.get(self.default, None)
        links = self.links.get(curr_node_name, None)
        if not links:
            return None
        for link in links:
            if link.condition == condition:
                return self.nodes.get(link.tail, None)
        return None


class ClientService(object):

    def __init__(self):
        endpoint_url = 'http://%s:%s' % (cfg.CONF.api.host, cfg.CONF.api.port)
        endpoints = {
            'action': endpoint_url,
            'reactor': endpoint_url,
            'datastore': endpoint_url,
        }
        self.client = Client(endpoints)

    def run_action(self, action_name, params, wait_for_completion=True):
        execution = models.ActionExecution()
        execution.action = {'name': action_name}
        execution.parameters = params
        action_exec_mgr = self.client.managers['ActionExecution']
        actionexec = action_exec_mgr.create(execution)
        while (wait_for_completion and
               actionexec.status != ACTIONEXEC_STATUS_COMPLETE and
               actionexec.status != ACTIONEXEC_STATUS_ERROR):
            eventlet.sleep(1)
            actionexec = action_exec_mgr.get_by_id(actionexec.id)
        return actionexec


class ActionChainRunner(ActionRunner):

    def __init__(self, id):
        self.id = id

    def pre_run(self):
        chainspec_file = self.entry_point
        LOG.debug('Reading action chain from %s for action %s.', chainspec_file,
                  self.action)
        try:
            with open(chainspec_file, 'r') as fd:
                chainspec = json.load(fd)
                self.action_chain = ActionChain(chainspec)
        except Exception as e:
            LOG.exception('Failed to instantiate ActionChain.')
            raise runnerexceptions.ActionRunnerPreRunError(e.message)
        self._client = ClientService()

    def run(self, action_parameters):
        action_node = self.action_chain.get_next_node()
        results = {}
        while action_node:
            actionexec = None
            try:
                resolved_params = ActionChainRunner._resolve_params(action_node, action_parameters,
                    results)
                actionexec = self._client.run_action(action_node.action_name, resolved_params)
            except:
                LOG.exception('Failure in running action %s.', action_node.name)
            else:
                # for now append all successful results
                results[action_node.name] = actionexec.result
            finally:
                if not actionexec or actionexec.status == ACTIONEXEC_STATUS_ERROR:
                    action_node = self.action_chain.get_next_node(action_node.name, 'on-failure')
                elif actionexec.status == ACTIONEXEC_STATUS_COMPLETE:
                    action_node = self.action_chain.get_next_node(action_node.name, 'on-success')
        self.container_service.report_result(results)
        return results is not None

    @staticmethod
    def _resolve_params(action_node, original_parameters, results):
        context = {}
        context.update(original_parameters)
        context.update(results)

        def template_loader(template_name):
            template = action_node.params[template_name]
            if isinstance(template, dict) or isinstance(template, list):
                return json.dumps(template)
            else:
                return str(template)

        env = jinja2.Environment(undefined=jinja2.StrictUndefined,
                                 loader=jinja2.FunctionLoader(template_loader))
        # TODO(manas) - generated params must be typed as per the expected schema.
        rendered_params = {}
        for k in action_node.params:
            rendered_v = env.get_template(k).render(context)
            rendered_params[k] = rendered_v
        return rendered_params


def get_runner():
    return ActionChainRunner(str(uuid.uuid4()))
