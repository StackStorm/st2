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

import copy
import uuid

import retrying
import six
import yaml
from mistralclient.api import client as mistral
from oslo_config import cfg

from st2actions.runners import AsyncActionRunner
from st2common.constants.action import LIVEACTION_STATUS_RUNNING
from st2common import log as logging
from st2common.models.api.notification import NotificationsHelper
from st2common.util.workflow import mistral as utils
from st2common.util.url import get_url_without_trailing_slash
from st2common.util.api import get_full_public_api_url
from st2common.util.api import get_mistral_api_url


LOG = logging.getLogger(__name__)


def get_runner():
    return MistralRunner(str(uuid.uuid4()))


class MistralRunner(AsyncActionRunner):

    url = get_url_without_trailing_slash(cfg.CONF.mistral.v2_base_url)

    def __init__(self, runner_id):
        super(MistralRunner, self).__init__(runner_id=runner_id)
        self._on_behalf_user = cfg.CONF.system_user.user
        self._notify = None
        self._skip_notify_tasks = []
        self._client = mistral.client(
            mistral_url=self.url,
            username=cfg.CONF.mistral.keystone_username,
            api_key=cfg.CONF.mistral.keystone_password,
            project_name=cfg.CONF.mistral.keystone_project_name,
            auth_url=cfg.CONF.mistral.keystone_auth_url,
            cacert=cfg.CONF.mistral.cacert,
            insecure=cfg.CONF.mistral.insecure)

    def pre_run(self):
        if getattr(self, 'liveaction', None):
            self._notify = getattr(self.liveaction, 'notify', None)
        self._skip_notify_tasks = self.runner_parameters.get('skip_notify', [])

    @staticmethod
    def _check_name(action_ref, is_workbook, def_dict):
        # If workbook, change the value of the "name" key.
        if is_workbook:
            if def_dict.get('name') != action_ref:
                raise Exception('Name of the workbook must be the same as the '
                                'fully qualified action name "%s".' % action_ref)
        # If workflow, change the key name of the workflow.
        else:
            workflow_name = [k for k, v in six.iteritems(def_dict) if k != 'version'][0]
            if workflow_name != action_ref:
                raise Exception('Name of the workflow must be the same as the '
                                'fully qualified action name "%s".' % action_ref)

    def _save_workbook(self, name, def_yaml):
        # If the workbook is not found, the mistral client throws a generic API exception.
        try:
            # Update existing workbook.
            wb = self._client.workbooks.get(name)
        except:
            # Delete if definition was previously a workflow.
            # If not found, an API exception is thrown.
            try:
                self._client.workflows.delete(name)
            except:
                pass

            # Create the new workbook.
            wb = self._client.workbooks.create(def_yaml)

        # Update the workbook definition.
        # pylint: disable=no-member
        if wb.definition != def_yaml:
            self._client.workbooks.update(def_yaml)

    def _save_workflow(self, name, def_yaml):
        # If the workflow is not found, the mistral client throws a generic API exception.
        try:
            # Update existing workbook.
            wf = self._client.workflows.get(name)
        except:
            # Delete if definition was previously a workbook.
            # If not found, an API exception is thrown.
            try:
                self._client.workbooks.delete(name)
            except:
                pass

            # Create the new workflow.
            wf = self._client.workflows.create(def_yaml)[0]

        # Update the workflow definition.
        # pylint: disable=no-member
        if wf.definition != def_yaml:
            self._client.workflows.update(def_yaml)

    def _find_default_workflow(self, def_dict):
        num_workflows = len(def_dict['workflows'].keys())

        if num_workflows > 1:
            fully_qualified_wf_name = self.runner_parameters.get('workflow')
            if not fully_qualified_wf_name:
                raise ValueError('Workbook definition is detected. '
                                 'Default workflow cannot be determined.')

            wf_name = fully_qualified_wf_name[fully_qualified_wf_name.rindex('.') + 1:]
            if wf_name not in def_dict['workflows']:
                raise ValueError('Unable to find the workflow "%s" in the workbook.'
                                 % fully_qualified_wf_name)

            return fully_qualified_wf_name
        elif num_workflows == 1:
            return '%s.%s' % (def_dict['name'], def_dict['workflows'].keys()[0])
        else:
            raise Exception('There are no workflows in the workbook.')

    def _construct_workflow_execution_options(self):
        # This URL is used by Mistral to talk back to the API
        api_url = get_mistral_api_url()
        endpoint = api_url + '/actionexecutions'

        # This URL is available in the context and can be used by the users inside a workflow,
        # similar to "ST2_ACTION_API_URL" environment variable available to actions
        public_api_url = get_full_public_api_url()

        # Build context with additional information
        parent_context = {
            'execution_id': self.execution_id
        }
        if getattr(self.liveaction, 'context', None):
            parent_context.update(self.liveaction.context)

        st2_execution_context = {
            'api_url': api_url,
            'endpoint': endpoint,
            'parent': parent_context,
            'notify': {},
            'skip_notify_tasks': self._skip_notify_tasks
        }

        # Include notification information
        if self._notify:
            notify_dict = NotificationsHelper.from_model(notify_model=self._notify)
            st2_execution_context['notify'] = notify_dict

        if self.auth_token:
            st2_execution_context['auth_token'] = self.auth_token.token

        options = {
            'env': {
                'st2_execution_id': self.execution_id,
                'st2_liveaction_id': self.liveaction_id,
                'st2_action_api_url': public_api_url,
                '__actions': {
                    'st2.action': {
                        'st2_context': st2_execution_context
                    }
                }
            }
        }

        return options

    def _get_resume_options(self):
        return self.context.get('re-run', {})

    @retrying.retry(
        retry_on_exception=utils.retry_on_exceptions,
        wait_exponential_multiplier=cfg.CONF.mistral.retry_exp_msec,
        wait_exponential_max=cfg.CONF.mistral.retry_exp_max_msec,
        stop_max_delay=cfg.CONF.mistral.retry_stop_max_msec)
    def run(self, action_parameters):
        resume_options = self._get_resume_options()

        tasks_to_reset = resume_options.get('reset', [])

        task_specs = {
            task_name: {'reset': task_name in tasks_to_reset}
            for task_name in resume_options.get('tasks', [])
        }

        resume = self.rerun_ex_ref and task_specs

        if resume:
            result = self.resume(ex_ref=self.rerun_ex_ref, task_specs=task_specs)
        else:
            result = self.start(action_parameters=action_parameters)

        return result

    def start(self, action_parameters):
        # Test connection
        self._client.workflows.list()

        # Setup inputs for the workflow execution.
        inputs = self.runner_parameters.get('context', dict())
        inputs.update(action_parameters)

        # Get workbook/workflow definition from file.
        with open(self.entry_point, 'r') as def_file:
            def_yaml = def_file.read()

        def_dict = yaml.safe_load(def_yaml)
        is_workbook = ('workflows' in def_dict)

        if not is_workbook:
            # Non-workbook definition containing multiple workflows is not supported.
            if len([k for k, _ in six.iteritems(def_dict) if k != 'version']) != 1:
                raise Exception('Workflow (not workbook) definition is detected. '
                                'Multiple workflows is not supported.')

        action_ref = '%s.%s' % (self.action.pack, self.action.name)
        self._check_name(action_ref, is_workbook, def_dict)
        def_dict_xformed = utils.transform_definition(def_dict)
        def_yaml_xformed = yaml.safe_dump(def_dict_xformed, default_flow_style=False)

        # Construct additional options for the workflow execution
        options = self._construct_workflow_execution_options()

        # Save workbook/workflow definition.
        if is_workbook:
            self._save_workbook(action_ref, def_yaml_xformed)
            default_workflow = self._find_default_workflow(def_dict_xformed)
            execution = self._client.executions.create(default_workflow,
                                                       workflow_input=inputs,
                                                       **options)
        else:
            self._save_workflow(action_ref, def_yaml_xformed)
            execution = self._client.executions.create(action_ref,
                                                       workflow_input=inputs,
                                                       **options)

        status = LIVEACTION_STATUS_RUNNING
        partial_results = {'tasks': []}

        # pylint: disable=no-member
        current_context = {
            'execution_id': str(execution.id),
            'workflow_name': execution.workflow_name
        }

        exec_context = self.context
        exec_context = self._build_mistral_context(exec_context, current_context)
        LOG.info('Mistral query context is %s' % exec_context)

        return (status, partial_results, exec_context)

    def _get_tasks(self, wf_ex_id, full_task_name, task_name, executions):
        task_exs = self._client.tasks.list(workflow_execution_id=wf_ex_id)

        if '.' in task_name:
            dot_pos = task_name.index('.')
            parent_task_name = task_name[:dot_pos]
            task_name = task_name[dot_pos + 1:]

            parent_task_ids = [task.id for task in task_exs if task.name == parent_task_name]

            workflow_ex_ids = [wf_ex.id for wf_ex in executions
                               if (getattr(wf_ex, 'task_execution_id', None) and
                                   wf_ex.task_execution_id in parent_task_ids)]

            tasks = {}

            for sub_wf_ex_id in workflow_ex_ids:
                tasks.update(self._get_tasks(sub_wf_ex_id, full_task_name, task_name, executions))

            return tasks

        # pylint: disable=no-member
        tasks = {
            full_task_name: task.to_dict()
            for task in task_exs
            if task.name == task_name and task.state == 'ERROR'
        }

        return tasks

    def resume(self, ex_ref, task_specs):
        mistral_ctx = ex_ref.context.get('mistral', dict())

        if not mistral_ctx.get('execution_id'):
            raise Exception('Unable to rerun because mistral execution_id is missing.')

        execution = self._client.executions.get(mistral_ctx.get('execution_id'))

        # pylint: disable=no-member
        if execution.state not in ['ERROR']:
            raise Exception('Workflow execution is not in a rerunable state.')

        executions = self._client.executions.list()

        tasks = {}

        for task_name, task_spec in six.iteritems(task_specs):
            tasks.update(self._get_tasks(execution.id, task_name, task_name, executions))

        missing_tasks = list(set(task_specs.keys()) - set(tasks.keys()))
        if missing_tasks:
            raise Exception('Only tasks in error state can be rerun. Unable to identify '
                            'rerunable tasks: %s. Please make sure that the task name is correct '
                            'and the task is in rerunable state.' % ', '.join(missing_tasks))

        # Construct additional options for the workflow execution
        options = self._construct_workflow_execution_options()

        for task_name, task_obj in six.iteritems(tasks):
            # pylint: disable=unexpected-keyword-arg
            self._client.tasks.rerun(
                task_obj['id'],
                reset=task_specs[task_name].get('reset', False),
                env=options.get('env', None)
            )

        status = LIVEACTION_STATUS_RUNNING
        partial_results = {'tasks': []}

        # pylint: disable=no-member
        current_context = {
            'execution_id': str(execution.id),
            'workflow_name': execution.workflow_name
        }

        exec_context = self.context
        exec_context = self._build_mistral_context(exec_context, current_context)
        LOG.info('Mistral query context is %s' % exec_context)

        return (status, partial_results, exec_context)

    @retrying.retry(
        retry_on_exception=utils.retry_on_exceptions,
        wait_exponential_multiplier=cfg.CONF.mistral.retry_exp_msec,
        wait_exponential_max=cfg.CONF.mistral.retry_exp_max_msec,
        stop_max_delay=cfg.CONF.mistral.retry_stop_max_msec)
    def cancel(self):
        mistral_ctx = self.context.get('mistral', dict())

        if not mistral_ctx.get('execution_id'):
            raise Exception('Unable to cancel because mistral execution_id is missing.')

        # There is no cancellation state in Mistral. Pause the workflow so
        # actions that are still executing can gracefully reach completion.
        self._client.executions.update(mistral_ctx.get('execution_id'), 'PAUSED')

    @staticmethod
    def _build_mistral_context(parent, current):
        """
        Mistral workflow might be kicked off in st2 by a parent Mistral
        workflow. In that case, we need to make sure that the existing
        mistral 'context' is moved as 'parent' and the child workflow
        'context' is added.
        """
        parent = copy.deepcopy(parent)
        context = dict()

        if not parent:
            context['mistral'] = current
        else:
            if 'mistral' in parent.keys():
                orig_parent_context = parent.get('mistral', dict())
                actual_parent = dict()
                if 'workflow_name' in orig_parent_context.keys():
                    actual_parent['workflow_name'] = orig_parent_context['workflow_name']
                    del orig_parent_context['workflow_name']
                if 'workflow_execution_id' in orig_parent_context.keys():
                    actual_parent['workflow_execution_id'] = \
                        orig_parent_context['workflow_execution_id']
                    del orig_parent_context['workflow_execution_id']
                context['mistral'] = orig_parent_context
                context['mistral'].update(current)
                context['mistral']['parent'] = actual_parent
            else:
                context['mistral'] = current

        return context
