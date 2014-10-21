import ast
import eventlet
import jinja2
import json
import six
import uuid

from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.exceptions import actionrunner as runnerexceptions
from st2common.models.db.action import ActionExecutionDB
from st2common.models.system.common import ResourceReference
from st2common.constants.action import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED
from st2common.services import action as action_service
from st2common.util import action_db as action_db_util


LOG = logging.getLogger(__name__)
RESULTS_KEY = '__results'


class ActionChain(object):

    class Node(object):

        def __init__(self, name, action_ref, params):
            self.name = name
            self.ref = action_ref
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
                node_name, node['ref'], node['params'])
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


class ActionChainRunner(ActionRunner):

    def __init__(self, id):
        super(ActionChainRunner, self).__init__()
        self.id = id
        self.action_chain = None

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

    def run(self, action_parameters):
        action_node = self.action_chain.get_next_node()
        results = {}
        fail = True
        while action_node:
            actionexec = None
            fail = False
            try:
                resolved_params = ActionChainRunner._resolve_params(action_node, action_parameters,
                                                                    results)
                actionexec = ActionChainRunner._run_action(action_node.ref,
                                                           self.action_execution_id,
                                                           resolved_params)
            except:
                LOG.exception('Failure in running action %s.', action_node.name)
            else:
                # for now append all successful results
                results[action_node.name] = actionexec.result
            finally:
                if not actionexec or actionexec.status == ACTIONEXEC_STATUS_FAILED:
                    fail = True
                    action_node = self.action_chain.get_next_node(action_node.name, 'on-failure')
                elif actionexec.status == ACTIONEXEC_STATUS_SUCCEEDED:
                    action_node = self.action_chain.get_next_node(action_node.name, 'on-success')
        self.container_service.report_result(results)
        if fail:
            self.container_service.report_status(ACTIONEXEC_STATUS_FAILED)
        else:
            self.container_service.report_status(ACTIONEXEC_STATUS_SUCCEEDED)
        return not fail

    @staticmethod
    def _resolve_params(action_node, original_parameters, results):
        # setup context with original parameters and the intermediate results.
        context = {}
        context.update(original_parameters)
        context.update(results)
        context.update({RESULTS_KEY: results})
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        rendered_params = {}
        for k, v in six.iteritems(action_node.params):
            # jinja2 works with string so transform list and dict to strings.
            reverse_json_dumps = False
            if isinstance(v, dict) or isinstance(v, list):
                v = json.dumps(v)
                reverse_json_dumps = True
            else:
                v = str(v)
            rendered_v = env.from_string(v).render(context)
            # no change therefore no templatization so pick params from original to retain
            # original type
            if rendered_v == v:
                rendered_params[k] = action_node.params[k]
                continue
            if reverse_json_dumps:
                rendered_v = json.loads(rendered_v)
            rendered_params[k] = rendered_v
        return rendered_params

    @staticmethod
    def _run_action(action_ref, parent_execution_id, params, wait_for_completion=True):
        execution = ActionExecutionDB(ref=action_ref)
        execution.parameters = ActionChainRunner._cast_params(action_ref, params)
        execution.context = {'parent': str(parent_execution_id)}
        execution = action_service.schedule(execution)
        while (wait_for_completion and
               execution.status != ACTIONEXEC_STATUS_SUCCEEDED and
               execution.status != ACTIONEXEC_STATUS_FAILED):
            eventlet.sleep(1)
            execution = action_db_util.get_actionexec_by_id(execution.id)
        return execution

    @staticmethod
    def _cast_params(action_ref, params):
        casts = {
            'array': (lambda x: ast.literal_eval(x) if isinstance(x, str) or isinstance(x, unicode)
                      else x),
            'boolean': (lambda x: ast.literal_eval(x.capitalize())
                        if isinstance(x, str) or isinstance(x, unicode) else x),
            'integer': int,
            'number': float,
            'object': (lambda x: json.loads(x) if isinstance(x, str) or isinstance(x, unicode)
                       else x),
            'string': str
        }

        action_db = action_db_util.get_action_by_ref(
            ResourceReference.from_string_reference(ref=action_ref))
        action_parameters_schema = action_db.parameters
        runnertype_db = action_db_util.get_runnertype_by_name(action_db.runner_type['name'])
        runner_parameters_schema = runnertype_db.runner_parameters
        # combine into 1 list of parameter schemas
        parameters_schema = {}
        if runner_parameters_schema:
            parameters_schema.update(runner_parameters_schema)
        if action_parameters_schema:
            parameters_schema.update(action_parameters_schema)
        # cast each param individually
        for k, v in six.iteritems(params):
            parameter_schema = parameters_schema.get(k, None)
            if not parameter_schema:
                continue
            parameter_type = parameter_schema.get('type', None)
            if not parameter_type:
                continue
            cast = casts.get(parameter_type, None)
            if not cast:
                continue
            params[k] = cast(v)
        return params


def get_runner():
    return ActionChainRunner(str(uuid.uuid4()))
