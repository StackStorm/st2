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

from __future__ import absolute_import
import copy
import eventlet
import traceback
import uuid
import datetime

from jsonschema import exceptions as json_schema_exc

from st2common.runners.base import ActionRunner
from st2common.runners.base import get_metadata as get_runner_metadata
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.constants import pack as pack_constants
from st2common.constants import keyvalue as kv_constants
from st2common.content.loader import MetaLoader
from st2common.exceptions import action as action_exc
from st2common.exceptions import actionrunner as runner_exc
from st2common.exceptions import db as db_exc
from st2common.models.api.notification import NotificationsHelper
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.system import actionchain
from st2common.models.utils import action_param_utils
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.services import action as action_service
from st2common.services import keyvalues as kv_service
from st2common.util import action_db as action_db_util
from st2common.util import isotime
from st2common.util import date as date_utils
from st2common.util import jinja as jinja_utils
from st2common.util import param as param_utils
from st2common.util.config_loader import get_config

__all__ = [
    'ActionChainRunner',
    'ChainHolder',

    'get_runner',
    'get_metadata'
]

LOG = logging.getLogger(__name__)

RESULTS_KEY = '__results'
JINJA_START_MARKERS = [
    '{{',
    '{%'
]
PUBLISHED_VARS_KEY = 'published'


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

        self.vars = {}

    def init_vars(self, action_parameters):
        if self.actionchain.vars:
            self.vars = self._get_rendered_vars(self.actionchain.vars,
                                                action_parameters=action_parameters)

    def restore_vars(self, ctx_vars):
        self.vars.update(copy.deepcopy(ctx_vars))

    def validate(self):
        """
        Function which performs a simple compile time validation.

        Keep in mind that some variables are only resolved during run time which means we can
        perform only simple validation during compile / create time.
        """
        all_nodes = self._get_all_nodes(action_chain=self.actionchain)

        for node in self.actionchain.chain:
            on_success_node_name = node.on_success
            on_failure_node_name = node.on_failure

            # Check "on-success" path
            valid_name = self._is_valid_node_name(all_node_names=all_nodes,
                                                  node_name=on_success_node_name)
            if not valid_name:
                msg = ('Unable to find node with name "%s" referenced in "on-success" in '
                       'task "%s".' % (on_success_node_name, node.name))
                raise ValueError(msg)

            # Check "on-failure" path
            valid_name = self._is_valid_node_name(all_node_names=all_nodes,
                                                  node_name=on_failure_node_name)
            if not valid_name:
                msg = ('Unable to find node with name "%s" referenced in "on-failure" in '
                       'task "%s".' % (on_failure_node_name, node.name))
                raise ValueError(msg)

        # check if node specified in default is valid.
        if self.actionchain.default:
            valid_name = self._is_valid_node_name(all_node_names=all_nodes,
                                                  node_name=self.actionchain.default)
            if not valid_name:
                msg = ('Unable to find node with name "%s" referenced in "default".' %
                       self.actionchain.default)
                raise ValueError(msg)
        return True

    @staticmethod
    def _get_default(action_chain):
        # default is defined
        if action_chain.default:
            return action_chain.default
        # no nodes in chain
        if not action_chain.chain:
            return None
        # The first node with no references is the default node. Assumptions
        # that support this are :
        # 1. There are no loops in the chain. Even if there are loops there is
        #    at least 1 node which does not end up in this loop.
        # 2. There are no fragments in the chain.
        all_nodes = ChainHolder._get_all_nodes(action_chain=action_chain)
        node_names = set(all_nodes)
        on_success_nodes = ChainHolder._get_all_on_success_nodes(action_chain=action_chain)
        on_failure_nodes = ChainHolder._get_all_on_failure_nodes(action_chain=action_chain)
        referenced_nodes = on_success_nodes | on_failure_nodes
        possible_default_nodes = node_names - referenced_nodes
        if possible_default_nodes:
            # This is to preserve order. set([..]) does not preserve the order so iterate
            # over original array.
            for node in all_nodes:
                if node in possible_default_nodes:
                    return node
        # If no node is found assume the first node in the chain list to be default.
        return action_chain.chain[0].name

    @staticmethod
    def _get_all_nodes(action_chain):
        """
        Return names for all the nodes in the chain.
        """
        all_nodes = [node.name for node in action_chain.chain]
        return all_nodes

    @staticmethod
    def _get_all_on_success_nodes(action_chain):
        """
        Return names for all the tasks referenced in "on-success".
        """
        on_success_nodes = set([node.on_success for node in action_chain.chain])
        return on_success_nodes

    @staticmethod
    def _get_all_on_failure_nodes(action_chain):
        """
        Return names for all the tasks referenced in "on-failure".
        """
        on_failure_nodes = set([node.on_failure for node in action_chain.chain])
        return on_failure_nodes

    def _is_valid_node_name(self, all_node_names, node_name):
        """
        Function which validates that the provided node name is defined in the workflow definition
        and it's valid.

        Keep in mind that we can only perform validation for task names which don't include jinja
        expressions since those are rendered at run time.
        """
        if not node_name:
            # This task name needs to be resolved during run time so we cant validate the name now
            return True

        is_jinja_expression = jinja_utils.is_jinja_expression(value=node_name)
        if is_jinja_expression:
            # This task name needs to be resolved during run time so we cant validate the name
            # now
            return True

        return node_name in all_node_names

    @staticmethod
    def _get_rendered_vars(vars, action_parameters):
        if not vars:
            return {}
        context = {}
        context.update({
            kv_constants.DATASTORE_PARENT_SCOPE: {
                kv_constants.SYSTEM_SCOPE: kv_service.KeyValueLookup(
                    scope=kv_constants.FULL_SYSTEM_SCOPE)
            }
        })
        context.update(action_parameters)
        LOG.info('Rendering action chain vars. Mapping = %s; Context = %s', vars, context)
        return jinja_utils.render_values(mapping=vars, context=context)

    def get_node(self, node_name=None, raise_on_failure=False):
        if not node_name:
            return None
        for node in self.actionchain.chain:
            if node.name == node_name:
                return node
        if raise_on_failure:
            raise runner_exc.ActionRunnerException(
                'Unable to find node with name "%s".' % (node_name))
        return None

    def get_next_node(self, curr_node_name=None, condition='on-success'):
        if not curr_node_name:
            return self.get_node(self.actionchain.default)
        current_node = self.get_node(curr_node_name)
        if condition == 'on-success':
            return self.get_node(current_node.on_success, raise_on_failure=True)
        elif condition == 'on-failure':
            return self.get_node(current_node.on_failure, raise_on_failure=True)
        raise runner_exc.ActionRunnerException('Unknown condition %s.' % condition)


class ActionChainRunner(ActionRunner):

    def __init__(self, runner_id):
        super(ActionChainRunner, self).__init__(runner_id=runner_id)
        self.chain_holder = None
        self._meta_loader = MetaLoader()
        self._skip_notify_tasks = []
        self._display_published = True
        self._chain_notify = None

    def pre_run(self):
        super(ActionChainRunner, self).pre_run()

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
            raise runner_exc.ActionRunnerPreRunError(message)

        try:
            self.chain_holder = ChainHolder(chainspec, self.action_name)
        except json_schema_exc.ValidationError as e:
            # preserve the whole nasty jsonschema message as that is better to get to the
            # root cause
            message = str(e)
            LOG.exception('Failed to instantiate ActionChain.')
            raise runner_exc.ActionRunnerPreRunError(message)
        except Exception as e:
            message = str(e)
            LOG.exception('Failed to instantiate ActionChain.')
            raise runner_exc.ActionRunnerPreRunError(message)

        # Runner attributes are set lazily. So these steps
        # should happen outside the constructor.
        if getattr(self, 'liveaction', None):
            self._chain_notify = getattr(self.liveaction, 'notify', None)
        if self.runner_parameters:
            self._skip_notify_tasks = self.runner_parameters.get('skip_notify', [])
            self._display_published = self.runner_parameters.get('display_published', True)

        # Perform some pre-run chain validation
        try:
            self.chain_holder.validate()
        except Exception as e:
            raise runner_exc.ActionRunnerPreRunError(str(e))

    def run(self, action_parameters):
        # Run the action chain.
        return self._run_chain(action_parameters)

    def cancel(self):
        # Identify the list of action executions that are workflows and cascade pause.
        for child_exec_id in self.execution.children:
            child_exec = ActionExecution.get(id=child_exec_id, raise_exception=True)
            if (child_exec.runner['name'] in action_constants.WORKFLOW_RUNNER_TYPES and
                    child_exec.status in action_constants.LIVEACTION_CANCELABLE_STATES):
                action_service.request_cancellation(
                    LiveAction.get(id=child_exec.liveaction['id']),
                    self.context.get('user', None)
                )

        return (
            action_constants.LIVEACTION_STATUS_CANCELING,
            self.liveaction.result,
            self.liveaction.context
        )

    def pause(self):
        # Identify the list of action executions that are workflows and cascade pause.
        for child_exec_id in self.execution.children:
            child_exec = ActionExecution.get(id=child_exec_id, raise_exception=True)
            if (child_exec.runner['name'] in action_constants.WORKFLOW_RUNNER_TYPES and
                    child_exec.status == action_constants.LIVEACTION_STATUS_RUNNING):
                action_service.request_pause(
                    LiveAction.get(id=child_exec.liveaction['id']),
                    self.context.get('user', None)
                )

        return (
            action_constants.LIVEACTION_STATUS_PAUSING,
            self.liveaction.result,
            self.liveaction.context
        )

    def resume(self):
        # Restore runner and action parameters since they are not provided on resume.
        runner_parameters, action_parameters = param_utils.render_final_params(
            self.runner_type.runner_parameters,
            self.action.parameters,
            self.liveaction.parameters,
            self.liveaction.context
        )

        # Assign runner parameters needed for pre-run.
        if runner_parameters:
            self.runner_parameters = runner_parameters

        # Restore chain holder if it is not initialized.
        if not self.chain_holder:
            self.pre_run()

        # Change the status of the liveaction from resuming to running.
        self.liveaction = action_service.update_status(
            self.liveaction,
            action_constants.LIVEACTION_STATUS_RUNNING,
            publish=False
        )

        # Run the action chain.
        return self._run_chain(action_parameters, resuming=True)

    def _run_chain(self, action_parameters, resuming=False):
        # Set chain status to fail unless explicitly set to succeed.
        chain_status = action_constants.LIVEACTION_STATUS_FAILED

        # Result holds the final result that the chain store in the database.
        result = {'tasks': []}

        # Save published variables into the result if specified.
        if self._display_published:
            result[PUBLISHED_VARS_KEY] = {}

        context_result = {}  # Holds result which is used for the template context purposes
        top_level_error = None  # Stores a reference to a top level error
        action_node = None
        last_task = None

        try:
            # Initialize vars with the action parameters.
            # This allows action parameers to be referenced from vars.
            self.chain_holder.init_vars(action_parameters)
        except Exception as e:
            chain_status = action_constants.LIVEACTION_STATUS_FAILED
            m = 'Failed initializing ``vars`` in chain.'
            LOG.exception(m)
            top_level_error = self._format_error(e, m)
            result.update(top_level_error)
            return (chain_status, result, None)

        # Restore state on resuming an existing chain execution.
        if resuming:
            # Restore vars is any from the liveaction.
            ctx_vars = self.liveaction.context.pop('vars', {})
            self.chain_holder.restore_vars(ctx_vars)

            # Restore result if any from the liveaction.
            if self.liveaction and hasattr(self.liveaction, 'result') and self.liveaction.result:
                result = self.liveaction.result

            # Initialize or rebuild existing context_result from liveaction
            # which holds the result used for resolving context in Jinja template.
            for task in result.get('tasks', []):
                context_result[task['name']] = task['result']

            # Restore or initialize the top_level_error
            # that stores a reference to a top level error.
            if 'error' in result or 'traceback' in result:
                top_level_error = {
                    'error': result.get('error'),
                    'traceback': result.get('traceback')
                }

        # If there are no executed tasks in the chain, then get the first node.
        if len(result['tasks']) <= 0:
            try:
                action_node = self.chain_holder.get_next_node()
            except Exception as e:
                m = 'Failed to get starting node "%s".', action_node.name
                LOG.exception(m)
                top_level_error = self._format_error(e, m)

            # If there are no action node to run next, then mark the chain successful.
            if not action_node:
                chain_status = action_constants.LIVEACTION_STATUS_SUCCEEDED

        # Otherwise, figure out the last task executed and
        # its state to determine where to begin executing.
        else:
            last_task = result['tasks'][-1]
            action_node = self.chain_holder.get_node(last_task['name'])
            liveaction = action_db_util.get_liveaction_by_id(last_task['liveaction_id'])

            # If the liveaction of the last task has changed, update the result entry.
            if liveaction.status != last_task['state']:
                updated_task_result = self._get_updated_action_exec_result(
                    action_node, liveaction, last_task)
                del result['tasks'][-1]
                result['tasks'].append(updated_task_result)

                # Also need to update context_result so the updated result
                # is available to Jinja expressions
                updated_task_name = updated_task_result['name']
                context_result[updated_task_name]['result'] = updated_task_result['result']

            # If the last task was canceled, then canceled the chain altogether.
            if liveaction.status == action_constants.LIVEACTION_STATUS_CANCELED:
                chain_status = action_constants.LIVEACTION_STATUS_CANCELED
                return (chain_status, result, None)

            # If the last task was paused, then stay on this action node.
            # This is explicitly put here for clarity.
            if liveaction.status == action_constants.LIVEACTION_STATUS_PAUSED:
                pass

            # If the last task succeeded, then get the next on-success action node.
            if liveaction.status == action_constants.LIVEACTION_STATUS_SUCCEEDED:
                chain_status = action_constants.LIVEACTION_STATUS_SUCCEEDED
                action_node = self.chain_holder.get_next_node(
                    last_task['name'], condition='on-success')

            # If the last task failed, then get the next on-failure action node.
            if liveaction.status in action_constants.LIVEACTION_FAILED_STATES:
                chain_status = action_constants.LIVEACTION_STATUS_FAILED
                action_node = self.chain_holder.get_next_node(
                    last_task['name'], condition='on-failure')

        # Setup parent context.
        parent_context = {
            'execution_id': self.execution_id
        }

        if getattr(self.liveaction, 'context', None):
            parent_context.update(self.liveaction.context)

        # Run the action chain until there are no more tasks.
        while action_node:
            error = None
            liveaction = None
            last_task = result['tasks'][-1] if len(result['tasks']) > 0 else None
            created_at = date_utils.get_datetime_utc_now()

            try:
                # If last task was paused, then fetch the liveaction and resume it first.
                if last_task and last_task['state'] == action_constants.LIVEACTION_STATUS_PAUSED:
                    liveaction = action_db_util.get_liveaction_by_id(last_task['liveaction_id'])
                    del result['tasks'][-1]
                else:
                    liveaction = self._get_next_action(
                        action_node=action_node, parent_context=parent_context,
                        action_params=action_parameters, context_result=context_result)
            except action_exc.InvalidActionReferencedException as e:
                chain_status = action_constants.LIVEACTION_STATUS_FAILED
                m = ('Failed to run task "%s". Action with reference "%s" doesn\'t exist.' %
                     (action_node.name, action_node.ref))
                LOG.exception(m)
                top_level_error = self._format_error(e, m)
                break
            except action_exc.ParameterRenderingFailedException as e:
                # Rendering parameters failed before we even got to running this action,
                # abort and fail the whole action chain
                chain_status = action_constants.LIVEACTION_STATUS_FAILED
                m = 'Failed to run task "%s". Parameter rendering failed.' % action_node.name
                LOG.exception(m)
                top_level_error = self._format_error(e, m)
                break
            except db_exc.StackStormDBObjectNotFoundError as e:
                chain_status = action_constants.LIVEACTION_STATUS_FAILED
                m = 'Failed to resume task "%s". Unable to find liveaction.' % action_node.name
                LOG.exception(m)
                top_level_error = self._format_error(e, m)
                break

            try:
                # If last task was paused, then fetch the liveaction and resume it first.
                if last_task and last_task['state'] == action_constants.LIVEACTION_STATUS_PAUSED:
                    LOG.info('Resume task %s for chain %s.', action_node.name, self.liveaction.id)
                    liveaction = self._resume_action(liveaction)
                else:
                    LOG.info('Run task %s for chain %s.', action_node.name, self.liveaction.id)
                    liveaction = self._run_action(liveaction)
            except Exception as e:
                # Save the traceback and error message
                m = 'Failed running task "%s".' % action_node.name
                LOG.exception(m)
                error = self._format_error(e, m)
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
                    if self._display_published:
                        result[PUBLISHED_VARS_KEY].update(rendered_publish_vars)
            finally:
                # Record result and resolve a next node based on the task success or failure
                updated_at = date_utils.get_datetime_utc_now()

                task_result = self._format_action_exec_result(
                    action_node,
                    liveaction,
                    created_at,
                    updated_at,
                    error=error
                )

                result['tasks'].append(task_result)

                try:
                    if not liveaction:
                        chain_status = action_constants.LIVEACTION_STATUS_FAILED
                        action_node = self.chain_holder.get_next_node(
                            action_node.name, condition='on-failure')
                    elif liveaction.status == action_constants.LIVEACTION_STATUS_TIMED_OUT:
                        chain_status = action_constants.LIVEACTION_STATUS_TIMED_OUT
                        action_node = self.chain_holder.get_next_node(
                            action_node.name, condition='on-failure')
                    elif liveaction.status == action_constants.LIVEACTION_STATUS_CANCELED:
                        LOG.info('Chain execution (%s) canceled because task "%s" is canceled.',
                                 self.liveaction_id, action_node.name)
                        chain_status = action_constants.LIVEACTION_STATUS_CANCELED
                        action_node = None
                    elif liveaction.status == action_constants.LIVEACTION_STATUS_PAUSED:
                        LOG.info('Chain execution (%s) paused because task "%s" is paused.',
                                 self.liveaction_id, action_node.name)
                        chain_status = action_constants.LIVEACTION_STATUS_PAUSED
                        self._save_vars()
                        action_node = None
                    elif liveaction.status in action_constants.LIVEACTION_FAILED_STATES:
                        chain_status = action_constants.LIVEACTION_STATUS_FAILED
                        action_node = self.chain_holder.get_next_node(
                            action_node.name, condition='on-failure')
                    elif liveaction.status == action_constants.LIVEACTION_STATUS_SUCCEEDED:
                        chain_status = action_constants.LIVEACTION_STATUS_SUCCEEDED
                        action_node = self.chain_holder.get_next_node(
                            action_node.name, condition='on-success')
                    else:
                        action_node = None
                except Exception as e:
                    chain_status = action_constants.LIVEACTION_STATUS_FAILED
                    m = 'Failed to get next node "%s".' % action_node.name
                    LOG.exception(m)
                    top_level_error = self._format_error(e, m)
                    action_node = None
                    break

            if action_service.is_action_canceled_or_canceling(self.liveaction.id):
                LOG.info('Chain execution (%s) canceled by user.', self.liveaction.id)
                chain_status = action_constants.LIVEACTION_STATUS_CANCELED
                return (chain_status, result, None)

            if action_service.is_action_paused_or_pausing(self.liveaction.id):
                LOG.info('Chain execution (%s) paused by user.', self.liveaction.id)
                chain_status = action_constants.LIVEACTION_STATUS_PAUSED
                self._save_vars()
                return (chain_status, result, self.liveaction.context)

        if top_level_error and isinstance(top_level_error, dict):
            result.update(top_level_error)

        return (chain_status, result, self.liveaction.context)

    def _format_error(self, e, msg):
        return {
            'error': '%s. %s' % (msg, str(e)),
            'traceback': traceback.format_exc(10)
        }

    def _save_vars(self):
        # Save the context vars in the liveaction context.
        self.liveaction.context['vars'] = self.chain_holder.vars

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

        context.update({
            kv_constants.SYSTEM_SCOPE: kv_service.KeyValueLookup(
                scope=kv_constants.SYSTEM_SCOPE)
        })

        context.update({
            kv_constants.DATASTORE_PARENT_SCOPE: {
                kv_constants.SYSTEM_SCOPE: kv_service.KeyValueLookup(
                    scope=kv_constants.FULL_SYSTEM_SCOPE)
            }
        })

        try:
            rendered_result = jinja_utils.render_values(mapping=action_node.publish,
                                                        context=context)
        except Exception as e:
            key = getattr(e, 'key', None)
            value = getattr(e, 'value', None)
            msg = ('Failed rendering value for publish parameter "%s" in task "%s" '
                   '(template string=%s): %s' % (key, action_node.name, value, str(e)))
            raise action_exc.ParameterRenderingFailedException(msg)

        return rendered_result

    @staticmethod
    def _resolve_params(action_node, original_parameters, results, chain_vars, chain_context):
        # setup context with original parameters and the intermediate results.
        chain_parent = chain_context.get('parent', {})
        pack = chain_parent.get('pack')
        user = chain_parent.get('user')

        config = get_config(pack, user)

        context = {}
        context.update(original_parameters)
        context.update(results)
        context.update(chain_vars)
        context.update({RESULTS_KEY: results})

        context.update({
            kv_constants.SYSTEM_SCOPE: kv_service.KeyValueLookup(
                scope=kv_constants.SYSTEM_SCOPE)
        })

        context.update({
            kv_constants.DATASTORE_PARENT_SCOPE: {
                kv_constants.SYSTEM_SCOPE: kv_service.KeyValueLookup(
                    scope=kv_constants.FULL_SYSTEM_SCOPE)
            }
        })
        context.update({action_constants.ACTION_CONTEXT_KV_PREFIX: chain_context})
        context.update({pack_constants.PACK_CONFIG_CONTEXT_KV_PREFIX: config})
        try:
            rendered_params = jinja_utils.render_values(mapping=action_node.get_parameters(),
                                                        context=context)
        except Exception as e:
            LOG.exception('Jinja rendering for parameter "%s" failed.' % (e.key))

            key = getattr(e, 'key', None)
            value = getattr(e, 'value', None)
            msg = ('Failed rendering value for action parameter "%s" in task "%s" '
                   '(template string=%s): %s') % (key, action_node.name, value, str(e))
            raise action_exc.ParameterRenderingFailedException(msg)
        LOG.debug('Rendered params: %s: Type: %s', rendered_params, type(rendered_params))
        return rendered_params

    def _get_next_action(self, action_node, parent_context, action_params, context_result):
        # Verify that the referenced action exists
        # TODO: We do another lookup in cast_param, refactor to reduce number of lookups
        task_name = action_node.name
        action_ref = action_node.ref
        action_db = action_db_util.get_action_by_ref(ref=action_ref)

        if not action_db:
            error = 'Task :: %s - Action with ref %s not registered.' % (task_name, action_ref)
            raise action_exc.InvalidActionReferencedException(error)

        resolved_params = ActionChainRunner._resolve_params(
            action_node=action_node, original_parameters=action_params,
            results=context_result, chain_vars=self.chain_holder.vars,
            chain_context={'parent': parent_context})

        liveaction = self._build_liveaction_object(
            action_node=action_node,
            resolved_params=resolved_params,
            parent_context=parent_context)

        return liveaction

    def _run_action(self, liveaction, wait_for_completion=True, sleep_delay=1.0):
        """
        :param sleep_delay: Number of seconds to wait during "is completed" polls.
        :type sleep_delay: ``float``
        """
        try:
            liveaction, _ = action_service.request(liveaction)
        except Exception as e:
            liveaction.status = action_constants.LIVEACTION_STATUS_FAILED
            LOG.exception('Failed to schedule liveaction.')
            raise e

        while (wait_for_completion and liveaction.status not in (
                action_constants.LIVEACTION_COMPLETED_STATES +
                [action_constants.LIVEACTION_STATUS_PAUSED])):
            eventlet.sleep(sleep_delay)
            liveaction = action_db_util.get_liveaction_by_id(liveaction.id)

        return liveaction

    def _resume_action(self, liveaction, wait_for_completion=True, sleep_delay=1.0):
        """
        :param sleep_delay: Number of seconds to wait during "is completed" polls.
        :type sleep_delay: ``float``
        """
        try:
            user = self.context.get('user', None)
            liveaction, _ = action_service.request_resume(liveaction, user)
        except Exception as e:
            liveaction.status = action_constants.LIVEACTION_STATUS_FAILED
            LOG.exception('Failed to schedule liveaction.')
            raise e

        while (wait_for_completion and liveaction.status not in (
                action_constants.LIVEACTION_COMPLETED_STATES +
                [action_constants.LIVEACTION_STATUS_PAUSED])):
            eventlet.sleep(sleep_delay)
            liveaction = action_db_util.get_liveaction_by_id(liveaction.id)

        return liveaction

    def _build_liveaction_object(self, action_node, resolved_params, parent_context):
        liveaction = LiveActionDB(action=action_node.ref)

        # Setup notify for task in chain.
        notify = self._get_notify(action_node)
        if notify:
            liveaction.notify = notify
            LOG.debug('%s: Task notify set to: %s', action_node.name, liveaction.notify)

        liveaction.context = {
            'parent': parent_context,
            'chain': vars(action_node)
        }
        liveaction.parameters = action_param_utils.cast_params(action_ref=action_node.ref,
                                                               params=resolved_params)
        return liveaction

    def _get_notify(self, action_node):
        if action_node.name not in self._skip_notify_tasks:
            if action_node.notify:
                task_notify = NotificationsHelper.to_model(action_node.notify)
                return task_notify
            elif self._chain_notify:
                return self._chain_notify

        return None

    def _get_updated_action_exec_result(self, action_node, liveaction, prev_task_result):
        if liveaction.status in action_constants.LIVEACTION_COMPLETED_STATES:
            created_at = isotime.parse(prev_task_result['created_at'])
            updated_at = liveaction.end_timestamp
        else:
            created_at = isotime.parse(prev_task_result['created_at'])
            updated_at = isotime.parse(prev_task_result['updated_at'])

        return self._format_action_exec_result(action_node, liveaction, created_at, updated_at)

    def _format_action_exec_result(self, action_node, liveaction_db, created_at, updated_at,
                                   error=None):
        """
        Format ActionExecution result so it can be used in the final action result output.

        :rtype: ``dict``
        """
        assert isinstance(created_at, datetime.datetime)
        assert isinstance(updated_at, datetime.datetime)

        result = {}

        execution_db = None
        if liveaction_db:
            execution_db = ActionExecution.get(liveaction__id=str(liveaction_db.id))

        result['id'] = action_node.name
        result['name'] = action_node.name
        result['execution_id'] = str(execution_db.id) if execution_db else None
        result['liveaction_id'] = str(liveaction_db.id) if liveaction_db else None
        result['workflow'] = None

        result['created_at'] = isotime.format(dt=created_at)
        result['updated_at'] = isotime.format(dt=updated_at)

        if error or not liveaction_db:
            result['state'] = action_constants.LIVEACTION_STATUS_FAILED
        else:
            result['state'] = liveaction_db.status

        if error:
            result['result'] = error
        else:
            result['result'] = liveaction_db.result

        return result


def get_runner():
    return ActionChainRunner(str(uuid.uuid4()))


def get_metadata():
    return get_runner_metadata('action_chain_runner')
