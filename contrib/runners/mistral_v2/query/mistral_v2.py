from __future__ import absolute_import
import random
import uuid

from mistralclient.api import base as mistralclient_base
from mistralclient.api import client as mistral
from oslo_config import cfg
import eventlet
import retrying

from st2common.query.base import Querier
from st2common.constants import action as action_constants
from st2common.exceptions import resultstracker as exceptions
from st2common import log as logging
from st2common.persistence.execution import ActionExecution
from st2common.util import action_db as action_utils
from st2common.util import jsonify
from st2common.util.url import get_url_without_trailing_slash
from st2common.util.workflow import mistral as utils


LOG = logging.getLogger(__name__)

DONE_STATES = {
    'ERROR': action_constants.LIVEACTION_STATUS_FAILED,
    'SUCCESS': action_constants.LIVEACTION_STATUS_SUCCEEDED,
    'CANCELLED': action_constants.LIVEACTION_STATUS_CANCELED,
    'PAUSED': action_constants.LIVEACTION_STATUS_PAUSED
}

ACTIVE_STATES = {
    'RUNNING': action_constants.LIVEACTION_STATUS_RUNNING
}

CANCELED_STATES = [
    action_constants.LIVEACTION_STATUS_CANCELED,
    action_constants.LIVEACTION_STATUS_CANCELING
]

PAUSED_STATES = [
    action_constants.LIVEACTION_STATUS_PAUSED,
    action_constants.LIVEACTION_STATUS_PAUSING
]

RESUMING_STATES = [
    action_constants.LIVEACTION_STATUS_RESUMING
]


def get_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))


class MistralResultsQuerier(Querier):
    delete_state_object_on_error = False

    def __init__(self, id, *args, **kwargs):
        super(MistralResultsQuerier, self).__init__(*args, **kwargs)
        self._base_url = get_url_without_trailing_slash(cfg.CONF.mistral.v2_base_url)
        self._client = mistral.client(
            mistral_url=self._base_url,
            username=cfg.CONF.mistral.keystone_username,
            api_key=cfg.CONF.mistral.keystone_password,
            project_name=cfg.CONF.mistral.keystone_project_name,
            auth_url=cfg.CONF.mistral.keystone_auth_url,
            cacert=cfg.CONF.mistral.cacert,
            insecure=cfg.CONF.mistral.insecure)
        self._jitter = cfg.CONF.mistral.jitter_interval

    @retrying.retry(
        retry_on_exception=utils.retry_on_exceptions,
        wait_exponential_multiplier=cfg.CONF.mistral.retry_exp_msec,
        wait_exponential_max=cfg.CONF.mistral.retry_exp_max_msec,
        stop_max_delay=cfg.CONF.mistral.retry_stop_max_msec)
    def query(self, execution_id, query_context, last_query_time=None):
        """
        Queries mistral for workflow results using v2 APIs.
        :param execution_id: st2 execution_id (context to be used for logging/audit)
        :type execution_id: ``str``
        :param query_context: context for the query to be made to mistral. This contains mistral
                              execution id.
        :type query_context: ``object``
        :param last_query_time: Timestamp of last query.
        :type last_query_time: ``float``
        :rtype: (``str``, ``object``)
        """
        # Retrieve liveaction_db to append new result to existing result.
        liveaction_db = action_utils.get_liveaction_by_id(execution_id)

        mistral_exec_id = query_context.get('mistral', {}).get('execution_id', None)
        if not mistral_exec_id:
            raise Exception('[%s] Missing mistral workflow execution ID in query context. %s',
                            execution_id, query_context)

        LOG.info('[%s] Querying mistral execution %s...', execution_id, mistral_exec_id)

        try:
            wf_result = self._get_workflow_result(execution_id, mistral_exec_id)

            stream = getattr(liveaction_db, 'result', {})

            wf_tasks_result = self._get_workflow_tasks(
                execution_id,
                mistral_exec_id,
                recorded_tasks=stream.get('tasks', [])
            )

            result = self._format_query_result(
                execution_id,
                mistral_exec_id,
                liveaction_db.result,
                wf_result,
                wf_tasks_result
            )
        except exceptions.ReferenceNotFoundError as exc:
            LOG.exception('[%s] Unable to find reference.', execution_id)
            return (action_constants.LIVEACTION_STATUS_FAILED, str(exc))
        except Exception:
            LOG.exception('[%s] Unable to fetch mistral workflow result and tasks. %s',
                          execution_id, query_context)
            raise

        # Retrieve liveaction_db again in case state has changed
        # while the querier get results from mistral API above.
        liveaction_db = action_utils.get_liveaction_by_id(execution_id)

        status = self._determine_execution_status(
            liveaction_db,
            result['extra']['state'],
            result['tasks']
        )

        LOG.info('[%s] Determined execution status: %s', execution_id, status)
        LOG.debug('[%s] Combined execution result: %s', execution_id, result)

        return (status, result)

    def _get_workflow_result(self, st2_exec_id, mistral_exec_id):
        """
        Returns the workflow status and output. Mistral workflow status will be converted
        to st2 action status.
        :param st2_exec_id: st2 execution ID
        :type st2_exec_id: ``str``
        :param mistral_exec_id: Mistral execution ID
        :type mistral_exec_id: ``str``
        :rtype: (``str``, ``dict``)
        """
        try:
            jitter = random.uniform(0, self._jitter)
            eventlet.sleep(jitter)
            execution = self._client.executions.get(mistral_exec_id)
        except mistralclient_base.APIException as mistral_exc:
            if 'not found' in str(mistral_exc):
                raise exceptions.ReferenceNotFoundError(str(mistral_exc))
            raise mistral_exc

        result = jsonify.try_loads(execution.output) if execution.state in DONE_STATES else {}

        result['extra'] = {
            'state': execution.state,
            'state_info': execution.state_info
        }

        LOG.info(
            '[%s] Query returned status "%s" for mistral execution %s.',
            st2_exec_id,
            execution.state,
            mistral_exec_id
        )

        return result

    def _get_workflow_tasks(self, st2_exec_id, mistral_exec_id, recorded_tasks=None):
        """
        Returns the list of tasks for a workflow execution.
        :param st2_exec_id: st2 execution ID
        :type st2_exec_id: ``str``
        :param mistral_exec_id: Mistral execution ID
        :type mistral_exec_id: ``str``
        :param recorded_tasks: The list of tasks recorded in the liveaction result.
        :rtype: ``list``
        """
        result = []
        queries = []

        if recorded_tasks is None:
            recorded_tasks = []

        try:
            wf_tasks = self._client.tasks.list(workflow_execution_id=mistral_exec_id)

            for wf_task in wf_tasks:
                recorded = list([x for x in recorded_tasks if x['id'] == wf_task.id])

                if (not recorded or
                        recorded[0].get('state') != wf_task.state or
                        str(recorded[0].get('created_at')) != wf_task.created_at or
                        str(recorded[0].get('updated_at')) != wf_task.updated_at):
                    queries.append(wf_task)

            target_task_names = [wf_task.name for wf_task in queries]

            LOG.info(
                '[%s] Querying the following tasks for mistral execution %s: %s',
                st2_exec_id,
                mistral_exec_id,
                ', '.join(target_task_names) if target_task_names else 'None'
            )

            for wf_task in queries:
                result.append(self._client.tasks.get(wf_task.id))

                # Lets not blast requests but just space it out for better CPU profile
                jitter = random.uniform(0, self._jitter)
                eventlet.sleep(jitter)
        except mistralclient_base.APIException as mistral_exc:
            if 'not found' in str(mistral_exc):
                raise exceptions.ReferenceNotFoundError(str(mistral_exc))
            raise mistral_exc

        return [self._format_task_result(task=entry.to_dict()) for entry in result]

    def _format_task_result(self, task):
        """
        Format task result to follow the unified workflow result format.
        """
        result = {
            'id': task['id'],
            'name': task['name'],
            'workflow_execution_id': task.get('workflow_execution_id', None),
            'workflow_name': task['workflow_name'],
            'created_at': task.get('created_at', None),
            'updated_at': task.get('updated_at', None),
            'state': task.get('state', None),
            'state_info': task.get('state_info', None),
            'type': task.get('type', None),
        }

        for attr in ['result', 'published']:
            result[attr] = jsonify.try_loads(task.get(attr, None))

        return result

    def _format_query_result(self, st2_exec_id, mistral_exec_id, current_result,
                             new_wf_result, new_wf_tasks_result):
        result = new_wf_result

        new_wf_task_ids = [entry['id'] for entry in new_wf_tasks_result]

        # get all of the task objects that existed in the livaction_db object
        # from the last time we checked on the results.
        # @note there could be no results, so the default is am empty list
        old_wf_tasks_result = [
            entry for entry in current_result.get('tasks', [])
            if entry['id'] not in new_wf_task_ids
        ]
        old_wf_task_ids = [entry['id'] for entry in old_wf_tasks_result]

        # @note We perform this extract in this funtion to avoid extracting
        # duplicate information over-over. By performing these API calls here
        # the inputs are only extracted when they are a in the new_wf_task_ids
        # list
        for task_result in new_wf_tasks_result:
            # if this task result is in the "old" list then skip it since we
            # extracted inputs from a previous run when it was "new"
            # or if 'input' has already been queried for and added to
            # the results
            if task_result['id'] in old_wf_task_ids:
                continue

            LOG.info(
                '[%s] Querying for inputs for mistral execution [%s] task [%s] name [%s]',
                st2_exec_id,
                mistral_exec_id,
                task_result['id'],
                '.'.join([task_result.get('workflow_name', 'None'),
                          task_result.get('name', 'None')])
            )

            if task_result.get('type', None) == 'ACTION':
                executions = self._client.action_executions.list(task_execution_id=task_result['id'])
            elif task_result.get('type', None) == 'WORKFLOW':
                executions = self._client.executions.list(task=task_result['id'])
            else:
                LOG.error('Unknown task type "{}" for task_execution.id: {}'.
                          format(task_result.get('type', None), task_result['id']))

            for exe in executions:
                exe_dict = exe.to_dict()

                # the input parameter contains serialized JSON, we need to parse
                # that to convert it into a dict
                input = jsonify.try_loads(exe_dict.get('input', None))
                if not input:
                    continue

                # In a StackStorm action (st2.action) the inputs for the action
                # are actually burried within a sub-field: input.parameters
                # In a non-StackStorm action the inputs are just a dict.
                if exe_dict.get('name', None) == 'st2.action':
                    task_result['input'] = input.get('parameters')
                    task_result['action'] = input.get('ref')
                else:
                    task_result['input'] = input
                    task_result['action'] = exe_dict.get('name', None)

                break

        result['tasks'] = old_wf_tasks_result + new_wf_tasks_result

        return result

    def _has_active_tasks(self, liveaction_db, mistral_wf_state, mistral_tasks):
        # Identify if there are any active tasks in Mistral.
        active_mistral_tasks = len([t for t in mistral_tasks if t['state'] in ACTIVE_STATES]) > 0

        active_st2_tasks = False
        execution = ActionExecution.get(liveaction__id=str(liveaction_db.id))

        for child_exec_id in execution.children:
            child_exec = ActionExecution.get(id=child_exec_id)

            # Catch exception where a child is requested twice due to st2mistral retrying
            # from a st2 API connection failure. The first child will be stuck in requested
            # while the mistral workflow is already completed.
            if (mistral_wf_state in DONE_STATES and
                    child_exec.status == action_constants.LIVEACTION_STATUS_REQUESTED):
                continue

            if (child_exec.status not in action_constants.LIVEACTION_COMPLETED_STATES and
                    child_exec.status != action_constants.LIVEACTION_STATUS_PAUSED):
                active_st2_tasks = True
                break

        if active_mistral_tasks:
            LOG.info('There are active mistral tasks for %s.', str(liveaction_db.id))

        if active_st2_tasks:
            LOG.info('There are active st2 tasks for %s.', str(liveaction_db.id))

        return active_mistral_tasks or active_st2_tasks

    def _determine_execution_status(self, liveaction_db, wf_state, tasks):
        # Determine if liveaction is being canceled, paused, or resumed.
        is_action_canceled = liveaction_db.status in CANCELED_STATES
        is_action_paused = liveaction_db.status in PAUSED_STATES
        is_action_resuming = liveaction_db.status in RESUMING_STATES

        # Identify the list of tasks that are still running or pausing.
        active_tasks = self._has_active_tasks(liveaction_db, wf_state, tasks)

        # Keep the execution in running state if there are active tasks.
        # In certain use cases, Mistral sets the workflow state to
        # completion prior to task completion.
        if is_action_canceled and active_tasks:
            status = action_constants.LIVEACTION_STATUS_CANCELING
        elif is_action_canceled and not active_tasks and wf_state not in DONE_STATES:
            status = action_constants.LIVEACTION_STATUS_CANCELING
        elif not is_action_canceled and active_tasks and wf_state == 'CANCELLED':
            status = action_constants.LIVEACTION_STATUS_CANCELING
        elif is_action_paused and active_tasks:
            status = action_constants.LIVEACTION_STATUS_PAUSING
        elif is_action_paused and not active_tasks and wf_state not in DONE_STATES:
            status = action_constants.LIVEACTION_STATUS_PAUSING
        elif not is_action_paused and active_tasks and wf_state == 'PAUSED':
            status = action_constants.LIVEACTION_STATUS_PAUSING
        elif is_action_resuming and wf_state == 'PAUSED':
            status = action_constants.LIVEACTION_STATUS_RESUMING
        elif wf_state in DONE_STATES and active_tasks:
            status = action_constants.LIVEACTION_STATUS_RUNNING
        elif wf_state in DONE_STATES and not active_tasks:
            status = DONE_STATES[wf_state]
        else:
            status = action_constants.LIVEACTION_STATUS_RUNNING

        return status
