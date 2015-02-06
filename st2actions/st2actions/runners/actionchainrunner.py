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

import ast
import eventlet
import jinja2
import json
import six
import traceback
import uuid
import datetime

from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.constants.action import (ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED)
from st2common.constants.system import SYSTEM_KV_PREFIX
from st2common.content.loader import MetaLoader
from st2common.exceptions import actionrunner as runnerexceptions
from st2common.models.db.action import ActionExecutionDB
from st2common.models.system import actionchain
from st2common.services import action as action_service
from st2common.services.keyvalues import KeyValueLookup
from st2common.util import action_db as action_db_util
from st2common.util import isotime


LOG = logging.getLogger(__name__)
RESULTS_KEY = '__results'


def render_values(values, context):
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    rendered_values = {}
    for k, v in six.iteritems(values):
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
            rendered_values[k] = values[k]
            continue
        if reverse_json_dumps:
            rendered_v = json.loads(rendered_v)
        rendered_values[k] = rendered_v
    return rendered_values


class ChainHolder(object):

    def __init__(self, chainspec, chainname):
        self.actionchain = actionchain.ActionChain(**chainspec)
        self.chainname = chainname
        if not self.actionchain.default:
            default = self._get_default(self.actionchain)
            self.actionchain.default = default
        LOG.debug('Using %s as default for %s.', self.actionchain.default, self.chainname)
        if not self.actionchain.default:
            raise Exception('Failed to find default node in %s.' % (self.chainname))
        # finalize the vars and save them around to be used at execution time.
        self.vars = self._get_rendered_vars(self.actionchain.vars) if self.actionchain.vars else {}

    @staticmethod
    def _get_default(_actionchain):
        # default is defined
        if _actionchain.default:
            return _actionchain.default
        # no nodes in chain
        if not _actionchain.chain:
            return None
        # The first node with no references is the default node. Assumptions
        # that support this are :
        # 1. There are no loops in the chain. Even if there are loops there is
        #    at least 1 node which does not end up in this loop.
        # 2. There are no fragments in the chain.
        node_names = set([node.name for node in _actionchain.chain])
        on_success_nodes = set([node.on_success for node in _actionchain.chain])
        on_failure_nodes = set([node.on_failure for node in _actionchain.chain])
        referenced_nodes = on_success_nodes | on_failure_nodes
        possible_default_nodes = node_names - referenced_nodes
        if possible_default_nodes:
            return possible_default_nodes.pop()
        # If no node is found assume the first node in the chain list to be default.
        return _actionchain.chain[0].name

    @staticmethod
    def _get_rendered_vars(vars):
        if not vars:
            return {}
        context = {SYSTEM_KV_PREFIX: KeyValueLookup()}
        return render_values(vars, context)

    def get_node(self, node_name=None):
        for node in self.actionchain.chain:
            if node.name == node_name:
                return node
        return None

    def get_next_node(self, curr_node_name=None, condition='on-success'):
        if not curr_node_name:
            return self.get_node(self.actionchain.default)
        current_node = self.get_node(curr_node_name)
        if condition == 'on-success':
            return self.get_node(current_node.on_success)
        elif condition == 'on-failure':
            return self.get_node(current_node.on_failure)
        raise runnerexceptions.ActionRunnerException('Unknown condition %s.' % condition)


class ActionChainRunner(ActionRunner):

    def __init__(self, runner_id):
        super(ActionChainRunner, self).__init__(runner_id=runner_id)
        self.chain_holder = None
        self._meta_loader = MetaLoader()

    def pre_run(self):
        chainspec_file = self.entry_point
        LOG.debug('Reading action chain from %s for action %s.', chainspec_file,
                  self.action)
        try:
            chainspec = self._meta_loader.load(chainspec_file)
            self.chain_holder = ChainHolder(chainspec, self.action_name)
        except Exception as e:
            LOG.exception('Failed to instantiate ActionChain.')
            raise runnerexceptions.ActionRunnerPreRunError(e.message)

    def run(self, action_parameters):
        action_node = self.chain_holder.get_next_node()

        result = {'tasks': []}  # holds final result we store
        context_result = {}  # holds result which is used for the template context purposes
        fail = True

        error = None

        while action_node:
            actionexec = None
            fail = False
            created_at = datetime.datetime.now()

            try:
                resolved_params = ActionChainRunner._resolve_params(
                    action_node=action_node, original_parameters=action_parameters,
                    results=context_result, chain_vars=self.chain_holder.vars)
                actionexec = ActionChainRunner._run_action(
                    action_node=action_node, parent_execution_id=self.action_execution_id,
                    params=resolved_params)
            except Exception:
                # Save the traceback and error message.
                LOG.exception('Failure in running action %s.', action_node.name)
                error = traceback.format_exc(10)
                context_result[action_node.name] = {'error': error}
            else:
                # Update context result
                context_result[action_node.name] = actionexec.result

                # Render and publish variables
                rendered_publish_vars = ActionChainRunner._render_publish_vars(
                    action_node=action_node, execution_result=actionexec.result,
                    previous_execution_results=context_result, chain_vars=self.chain_holder.vars)

                if rendered_publish_vars:
                    self.chain_holder.vars.update(rendered_publish_vars)
            finally:
                # Record result and resolve a next node based on the task success or failure
                updated_at = datetime.datetime.now()

                format_kwargs = {'action_node': action_node, 'action_exec_db': actionexec,
                                 'created_at': created_at, 'updated_at': updated_at}

                if error:
                    format_kwargs['error'] = error

                task_result = self._format_action_exec_result(**format_kwargs)
                result['tasks'].append(task_result)

                if not actionexec or actionexec.status == ACTIONEXEC_STATUS_FAILED:
                    fail = True
                    action_node = self.chain_holder.get_next_node(action_node.name, 'on-failure')
                elif actionexec.status == ACTIONEXEC_STATUS_SUCCEEDED:
                    action_node = self.chain_holder.get_next_node(action_node.name, 'on-success')

        if fail:
            status = ACTIONEXEC_STATUS_FAILED
        else:
            status = ACTIONEXEC_STATUS_SUCCEEDED

        return (status, result)

    @staticmethod
    def _render_publish_vars(action_node, execution_result, previous_execution_results,
                             chain_vars):
        """
        If no output is specified on the action_node the output is the entire execution_result.
        If any output is specified then only those variables are published as output of an
        execution of this action_node.
        The output variable can refer to a variable from the execution_result,
        previous_execution_results or chain_vars.
        """
        if not action_node.publish:
            return {}
        context = {}
        context.update({action_node.name: execution_result})
        context.update(previous_execution_results)
        context.update(chain_vars)
        context.update({RESULTS_KEY: previous_execution_results})
        context.update({SYSTEM_KV_PREFIX: KeyValueLookup()})
        rendered_result = render_values(action_node.publish, context)
        return rendered_result

    @staticmethod
    def _resolve_params(action_node, original_parameters, results, chain_vars):
        # setup context with original parameters and the intermediate results.
        context = {}
        context.update(original_parameters)
        context.update(results)
        context.update(chain_vars)
        context.update({RESULTS_KEY: results})
        context.update({SYSTEM_KV_PREFIX: KeyValueLookup()})
        rendered_params = render_values(action_node.params, context)
        LOG.debug('Rendered params: %s: Type: %s', rendered_params, type(rendered_params))
        return rendered_params

    @staticmethod
    def _run_action(action_node, parent_execution_id, params, wait_for_completion=True):
        execution = ActionExecutionDB(action=action_node.ref)
        execution.parameters = ActionChainRunner._cast_params(action_node.ref, params)
        execution.context = {
            'parent': str(parent_execution_id),
            'chain': vars(action_node)
        }
        execution = action_service.schedule(execution)
        while (wait_for_completion and
               execution.status != ACTIONEXEC_STATUS_SUCCEEDED and
               execution.status != ACTIONEXEC_STATUS_FAILED):
            eventlet.sleep(1)
            execution = action_db_util.get_actionexec_by_id(execution.id)
        return execution

    def _format_action_exec_result(self, action_node, action_exec_db, created_at, updated_at,
                                   error=None):
        """
        Format ActionExecution result so it can be used in the final action result output.

        :rtype: ``dict``
        """
        assert(isinstance(created_at, datetime.datetime))
        assert(isinstance(updated_at, datetime.datetime))

        result = {}

        result['id'] = action_node.name
        result['name'] = action_node.name
        result['execution_id'] = str(action_exec_db.id) if action_exec_db else None
        result['mistral_execution_id'] = None
        result['workflow'] = None

        result['created_at'] = isotime.format(dt=created_at)
        result['updated_at'] = isotime.format(dt=updated_at)

        if error or not action_exec_db:
            result['state'] = ACTIONEXEC_STATUS_FAILED
        else:
            result['state'] = action_exec_db.status

        if error:
            result['result'] = {'error': error}
        else:
            result['result'] = action_exec_db.result

        return result

    @staticmethod
    def _cast_params(action_ref, params):
        def cast_object(x):
            if isinstance(x, str) or isinstance(x, unicode):
                try:
                    return json.loads(x)
                except:
                    return ast.literal_eval(x)
            else:
                return x

        casts = {
            'array': (lambda x: ast.literal_eval(x) if isinstance(x, str) or isinstance(x, unicode)
                      else x),
            'boolean': (lambda x: ast.literal_eval(x.capitalize())
                        if isinstance(x, str) or isinstance(x, unicode) else x),
            'integer': int,
            'number': float,
            'object': cast_object,
            'string': str
        }

        action_db = action_db_util.get_action_by_ref(action_ref)
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
            LOG.debug('Casting param: %s of type %s to type: %s', v, type(v), parameter_type)
            if not cast:
                continue
            params[k] = cast(v)
        return params


def get_runner():
    return ActionChainRunner(str(uuid.uuid4()))
