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

import eventlet
import traceback
import uuid
import datetime

from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.constants.action import (LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED)
from st2common.constants.action import LIVEACTION_STATUS_CANCELED
from st2common.constants.system import SYSTEM_KV_PREFIX
from st2common.content.loader import MetaLoader
from st2common.exceptions import actionrunner as runnerexceptions
from st2common.models.api.notification import NotificationsHelper
from st2common.models.db.action import LiveActionDB
from st2common.models.system import actionchain
from st2common.models.utils import action_param_utils
from st2common.persistence.execution import ActionExecution
from st2common.services import action as action_service
from st2common.services.keyvalues import KeyValueLookup
from st2common.util import action_db as action_db_util
from st2common.util import isotime
from st2common.util import jinja as jinja_utils


LOG = logging.getLogger(__name__)
RESULTS_KEY = '__results'


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
        all_nodes = [node.name for node in _actionchain.chain]
        node_names = set(all_nodes)
        on_success_nodes = set([node.on_success for node in _actionchain.chain])
        on_failure_nodes = set([node.on_failure for node in _actionchain.chain])
        referenced_nodes = on_success_nodes | on_failure_nodes
        possible_default_nodes = node_names - referenced_nodes
        if possible_default_nodes:
            # This is to preserve order. set([..]) does not preserve the order so iterate
            # over original array.
            for node in all_nodes:
                if node in possible_default_nodes:
                    return node
        # If no node is found assume the first node in the chain list to be default.
        return _actionchain.chain[0].name

    @staticmethod
    def _get_rendered_vars(vars):
        if not vars:
            return {}
        context = {SYSTEM_KV_PREFIX: KeyValueLookup()}
        return jinja_utils.render_values(mapping=vars, context=context)

    def get_node(self, node_name=None, raise_on_failure=False):
        if not node_name:
            return None
        for node in self.actionchain.chain:
            if node.name == node_name:
                return node
        if raise_on_failure:
            raise runnerexceptions.ActionRunnerException('Unable to find node with name "%s".' %
                                                         (node_name))
        return None

    def get_next_node(self, curr_node_name=None, condition='on-success'):
        if not curr_node_name:
            return self.get_node(self.actionchain.default)
        current_node = self.get_node(curr_node_name)
        if condition == 'on-success':
            return self.get_node(current_node.on_success, raise_on_failure=True)
        elif condition == 'on-failure':
            return self.get_node(current_node.on_failure, raise_on_failure=True)
        raise runnerexceptions.ActionRunnerException('Unknown condition %s.' % condition)


class ActionChainRunner(ActionRunner):

    def __init__(self, runner_id):
        super(ActionChainRunner, self).__init__(runner_id=runner_id)
        self.chain_holder = None
        self._meta_loader = MetaLoader()
        self._stopped = False

    def pre_run(self):
        chainspec_file = self.entry_point
        LOG.debug('Reading action chain from %s for action %s.', chainspec_file,
                  self.action)

        try:
            chainspec = self._meta_loader.load(file_path=chainspec_file,
                                               expected_type=dict)
        except Exception as e:
            message = ('Failed to parse action chain definition from "%s": %s' %
                       (chainspec_file, str(e)))
            LOG.exception('Failed to load action chain definition.')
            raise runnerexceptions.ActionRunnerPreRunError(message)

        try:
            self.chain_holder = ChainHolder(chainspec, self.action_name)
        except Exception as e:
            message = e.message or str(e)
            LOG.exception('Failed to instantiate ActionChain.')
            raise runnerexceptions.ActionRunnerPreRunError(message)

    def run(self, action_parameters):
        result = {'tasks': []}  # holds final result we store
        context_result = {}  # holds result which is used for the template context purposes
        top_level_error = None  # stores a reference to a top level error
        fail = True
        action_node = None

        try:
            action_node = self.chain_holder.get_next_node()
        except Exception as e:
            LOG.exception('Failed to get starting node "%s".', action_node.name)

            error = ('Failed to get starting node "%s". Lookup failed: %s' %
                     (action_node.name, str(e)))
            trace = traceback.format_exc(10)
            top_level_error = {
                'error': error,
                'traceback': trace
            }

        while action_node:
            fail = False
            error = None
            resolved_params = None
            liveaction = None

            created_at = datetime.datetime.now()

            try:
                resolved_params = ActionChainRunner._resolve_params(
                    action_node=action_node, original_parameters=action_parameters,
                    results=context_result, chain_vars=self.chain_holder.vars)
            except Exception as e:
                # Rendering parameters failed before we even got to running this action, abort and
                # fail the whole action chain
                LOG.exception('Failed to run action "%s".', action_node.name)

                fail = True
                error = ('Failed to run task "%s". Parameter rendering failed: %s' %
                         (action_node.name, str(e)))
                trace = traceback.format_exc(10)
                top_level_error = {
                    'error': error,
                    'traceback': trace
                }
                break

            # Verify that the referenced action exists
            # TODO: We do another lookup in cast_param, refactor to reduce number of lookups
            action_ref = action_node.ref
            action_db = action_db_util.get_action_by_ref(ref=action_ref)

            if not action_db:
                error = ('Failed to run task "%s". Action with reference "%s" doesn\'t exist.' %
                         (action_node.name, action_ref))
                LOG.exception(error)

                fail = True
                top_level_error = {
                    'error': error,
                    'traceback': error
                }
                break

            try:
                liveaction = self._run_action(
                    action_node=action_node, parent_execution_id=self.liveaction_id,
                    params=resolved_params)
            except Exception as e:
                # Save the traceback and error message
                LOG.exception('Failure in running action "%s".', action_node.name)

                error = {
                    'error': 'Task "%s" failed: %s' % (action_node.name, str(e)),
                    'traceback': traceback.format_exc(10)
                }
                context_result[action_node.name] = error
            else:
                # Update context result
                context_result[action_node.name] = liveaction.result

                # Render and publish variables
                rendered_publish_vars = ActionChainRunner._render_publish_vars(
                    action_node=action_node, action_parameters=action_parameters,
                    execution_result=liveaction.result, previous_execution_results=context_result,
                    chain_vars=self.chain_holder.vars)

                if rendered_publish_vars:
                    self.chain_holder.vars.update(rendered_publish_vars)
            finally:
                # Record result and resolve a next node based on the task success or failure
                updated_at = datetime.datetime.now()

                format_kwargs = {'action_node': action_node, 'liveaction_db': liveaction,
                                 'created_at': created_at, 'updated_at': updated_at}

                if error:
                    format_kwargs['error'] = error

                task_result = self._format_action_exec_result(**format_kwargs)
                result['tasks'].append(task_result)

                if self.liveaction_id:
                    self._stopped = action_service.is_action_canceled(self.liveaction_id)

                if not self._stopped:
                    try:
                        if not liveaction or liveaction.status == LIVEACTION_STATUS_FAILED:
                            fail = True
                            action_node = self.chain_holder.get_next_node(action_node.name,
                                                                          condition='on-failure')
                        elif liveaction.status == LIVEACTION_STATUS_SUCCEEDED:
                            action_node = self.chain_holder.get_next_node(action_node.name,
                                                                          condition='on-success')
                    except Exception as e:
                        LOG.exception('Failed to get next node "%s".', action_node.name)

                        fail = True
                        error = ('Failed to get next node "%s". Lookup failed: %s' %
                                 (action_node.name, str(e)))
                        trace = traceback.format_exc(10)
                        top_level_error = {
                            'error': error,
                            'traceback': trace
                        }
                        # reset action_node here so that chain breaks on failure.
                        action_node = None
                else:
                    LOG.info('Chain execution (%s) canceled by user.', self.liveaction_id)
                    status = LIVEACTION_STATUS_CANCELED
                    return (status, result, None)

        if fail:
            status = LIVEACTION_STATUS_FAILED
        else:
            status = LIVEACTION_STATUS_SUCCEEDED

        if top_level_error:
            # Include top level error information
            result['error'] = top_level_error['error']
            result['traceback'] = top_level_error['traceback']

        return (status, result, None)

    @staticmethod
    def _render_publish_vars(action_node, action_parameters, execution_result,
                             previous_execution_results, chain_vars):
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
        context.update(action_parameters)
        context.update({action_node.name: execution_result})
        context.update(previous_execution_results)
        context.update(chain_vars)
        context.update({RESULTS_KEY: previous_execution_results})
        context.update({SYSTEM_KV_PREFIX: KeyValueLookup()})
        rendered_result = jinja_utils.render_values(mapping=action_node.publish, context=context)
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
        rendered_params = jinja_utils.render_values(mapping=action_node.params, context=context)
        LOG.debug('Rendered params: %s: Type: %s', rendered_params, type(rendered_params))
        return rendered_params

    def _run_action(self, action_node, parent_execution_id, params, wait_for_completion=True):
        parent_notify = None
        if getattr(self, 'liveaction', None):
            parent_notify = getattr(self.liveaction, 'notify', None)
        liveaction = LiveActionDB(action=action_node.ref)
        liveaction.parameters = action_param_utils.cast_params(action_ref=action_node.ref,
                                                               params=params)
        if action_node.notify:
            liveaction.notify = NotificationsHelper.to_model(action_node.notify)
        elif parent_notify:
            print('Parent_notify = %s', parent_notify)
            liveaction.notify = parent_notify

        liveaction.context = {
            'parent': str(parent_execution_id),
            'chain': vars(action_node)
        }

        liveaction, _ = action_service.schedule(liveaction)

        while (wait_for_completion and
               liveaction.status != LIVEACTION_STATUS_SUCCEEDED and
               liveaction.status != LIVEACTION_STATUS_FAILED):
            eventlet.sleep(1)
            liveaction = action_db_util.get_liveaction_by_id(liveaction.id)

        return liveaction

    def _format_action_exec_result(self, action_node, liveaction_db, created_at, updated_at,
                                   error=None):
        """
        Format ActionExecution result so it can be used in the final action result output.

        :rtype: ``dict``
        """
        assert(isinstance(created_at, datetime.datetime))
        assert(isinstance(updated_at, datetime.datetime))

        result = {}

        execution_db = None
        if liveaction_db:
            execution_db = ActionExecution.get(liveaction__id=str(liveaction_db.id))

        result['id'] = action_node.name
        result['name'] = action_node.name
        result['execution_id'] = str(execution_db.id) if execution_db else None
        result['workflow'] = None

        result['created_at'] = isotime.format(dt=created_at)
        result['updated_at'] = isotime.format(dt=updated_at)

        if error or not liveaction_db:
            result['state'] = LIVEACTION_STATUS_FAILED
        else:
            result['state'] = liveaction_db.status

        if error:
            result['result'] = error
        else:
            result['result'] = liveaction_db.result

        return result


def get_runner():
    return ActionChainRunner(str(uuid.uuid4()))
