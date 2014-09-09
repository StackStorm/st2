import datetime
import eventlet
import json
import jsonschema
import pecan
from pecan import abort
from pecan.rest import RestController
import six
import Queue

from oslo.config import cfg

from st2common import log as logging
from st2common.models.base import jsexpose
from st2common.persistence.action import ActionExecution
from st2common.models.api.action import (ActionExecutionAPI,
                                         ACTIONEXEC_STATUS_INIT,
                                         ACTIONEXEC_STATUS_SCHEDULED,
                                         ACTIONEXEC_STATUS_ERROR)
from st2common.util import schema as util_schema
from st2common import transport
from st2common.util.action_db import (get_action_by_dict, update_actionexecution_status,
                                      get_runnertype_by_name)

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


MONITOR_THREAD_EMPTY_Q_SLEEP_TIME = 5
MONITOR_THREAD_NO_WORKERS_SLEEP_TIME = 1


class ActionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    def __init__(self, live_actions_pool_size=50):
        self.live_actions_pool_size = live_actions_pool_size
        self._live_actions_pool = eventlet.GreenPool(self.live_actions_pool_size)
        self._threads = {}
        self._live_actions = Queue.Queue()
        self._live_actions_monitor_thread = eventlet.greenthread.spawn(self._drain_live_actions)
        self._monitor_thread_empty_q_sleep_time = MONITOR_THREAD_EMPTY_Q_SLEEP_TIME
        self._monitor_thread_no_workers_sleep_time = MONITOR_THREAD_NO_WORKERS_SLEEP_TIME
        self._publisher = transport.actionexecution.ActionExecutionPublisher(
            cfg.CONF.messaging.url)

    def _issue_liveaction_post(self, actionexec_id):
        """
            Launch the ActionExecution specified by actionexec_id by performing
            a POST against the /liveactions/ http endpoint.
        """

        payload = self._create_liveaction_data(actionexec_id)
        LOG.info('Issuing /liveactions/ POST data=%s', payload)
        request_error = False
        result = None
        try:
            self._publisher.publish_create(json.dumps(payload))
        except Exception:
            LOG.exception('Unable to publish to exchange.')
            request_error = True

        LOG.debug('/liveactions/ POST request result: status: %s body: %s', result,
                  result.text if result else None)

        return (result, request_error)

    @staticmethod
    def __get_by_id(id):
        try:
            return ActionExecution.get_by_id(id)
        except Exception as e:
            msg = 'Database lookup for id="%s" resulted in exception. %s' % (id, e)
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)

    @staticmethod
    def _get_action_executions(action_id, action_name, limit=None):
        if action_id is not None:
            LOG.debug('Using action_id=%s to get action executions', action_id)
            # action__id <- this queries action.id
            return ActionExecution.query(action__id=action_id,
                                         order_by=['-start_timestamp'],
                                         limit=limit)
        elif action_name is not None:
            LOG.debug('Using action_name=%s to get action executions', action_name)
            # action__name <- this queries against action.name
            return ActionExecution.query(action__name=action_name,
                                         order_by=['-start_timestamp'],
                                         limit=limit)
        LOG.debug('Retrieving all action executions')
        return ActionExecution.get_all(order_by=['-start_timestamp'],
                                       limit=limit)

    def _create_liveaction_data(self, actionexecution_id):
        return {'actionexecution_id': str(actionexecution_id)}

    @jsexpose(str)
    def get_one(self, id):
        """
            List actionexecution by id.

            Handle:
                GET /actionexecutions/1
        """
        LOG.info('GET /actionexecutions/ with id=%s', id)
        actionexec_db = ActionExecutionsController.__get_by_id(id)
        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)
        LOG.debug('GET /actionexecutions/ with id=%s, client_result=%s', id, actionexec_api)
        return actionexec_api

    @jsexpose(str, str, str)
    def get_all(self, action_id=None, action_name=None, limit='50'):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """

        LOG.info('GET all /actionexecutions/ with action_name=%s, '
                 'action_id=%s, and limit=%s', action_name, action_id, limit)

        actionexec_dbs = ActionExecutionsController._get_action_executions(
            action_id, action_name, limit=int(limit))
        actionexec_apis = [ActionExecutionAPI.from_model(actionexec_db)
                           for actionexec_db
                           in sorted(actionexec_dbs,
                                     key=lambda x: x.start_timestamp)]

        # TODO: unpack list in log message
        LOG.debug('GET all /actionexecutions/ client_result=%s', actionexec_apis)
        return actionexec_apis

    @jsexpose(body=ActionExecutionAPI, status_code=http_client.CREATED)
    def post(self, actionexecution):
        """
            Create a new actionexecution.

            Handles requests:
                POST /actionexecutions/
        """

        LOG.info('POST /actionexecutions/ with actionexec data=%s', actionexecution)

        actionexecution.start_timestamp = datetime.datetime.now()

        # Retrieve context from request header.
        if ('st2-context' in pecan.request.headers and pecan.request.headers['st2-context']):
            context = pecan.request.headers['st2-context'].replace("'", "\"")
            actionexecution.context = json.loads(context)

        # Fill-in runner_parameters and action_parameter fields if they are not
        # provided in the request.
        if not hasattr(actionexecution, 'parameters'):
            LOG.warning('POST /actionexecutions/ request did not '
                        'provide parameters field.')
            setattr(actionexecution, 'runner_parameters', {})

        (action_db, action_dict) = get_action_by_dict(actionexecution.action)
        LOG.debug('POST /actionexecutions/ Action=%s', action_db)

        if not action_db:
            LOG.error('POST /actionexecutions/ Action for "%s" cannot be found.',
                      actionexecution.action)
            abort(http_client.NOT_FOUND, 'Unable to find action.')
            return

        actionexecution.action = action_dict

        # If the Action is disabled, abort the POST call.
        if not action_db.enabled:
            LOG.error('POST /actionexecutions/ Unable to create Action Execution for a disabled '
                      'Action. Action is: %s', action_db)
            abort(http_client.FORBIDDEN, 'Action is disabled.')
            return

        # Assign default parameters
        runnertype = get_runnertype_by_name(action_db.runner_type['name'])
        LOG.debug('POST /actionexecutions/ Runner=%s', runnertype)
        for key, metadata in six.iteritems(runnertype.runner_parameters):
            if key not in actionexecution.parameters and 'default' in metadata:
                if metadata.get('default') is not None:
                    actionexecution.parameters[key] = metadata['default']

        # Validate action parameters
        schema = util_schema.get_parameter_schema(action_db)
        try:
            LOG.debug('POST /actionexecutions/ Validation for parameters=%s & schema=%s',
                      actionexecution.parameters, schema)
            jsonschema.validate(actionexecution.parameters, schema)
            LOG.debug('POST /actionexecutions/ Parameter validation passed.')
        except jsonschema.ValidationError as e:
            LOG.error('POST /actionexecutions/ Parameter validation failed. %s', actionexecution)
            abort(http_client.BAD_REQUEST, str(e))
            return

        # Set initial value for ActionExecution status.
        # Not using update_actionexecution_status to allow other initialization to
        # be done before saving to DB.
        actionexecution.status = ACTIONEXEC_STATUS_INIT
        actionexec_db = ActionExecutionAPI.to_model(actionexecution)
        actionexec_db = ActionExecution.add_or_update(actionexec_db)
        LOG.audit('ActionExecution created. ActionExecution=%s. ', actionexec_db)

        actionexec_id = actionexec_db.id
        try:
            LOG.debug('Adding action exec id: %s to live actions queue.', )
            self._live_actions.put(actionexec_id, block=True, timeout=1)
        except Exception as e:
            LOG.exception('Aborting /actionexecutions/ POST operation for id: %s.', actionexec_id)
            actionexec_status = ACTIONEXEC_STATUS_ERROR
            actionexec_db = update_actionexecution_status(actionexec_status,
                                                          actionexec_id=actionexec_id)
            actionexec_api = ActionExecutionAPI.from_model(actionexec_db)
            error = 'Failed to kickoff live action for id: %s, exception: %s' % (actionexec_id,
                                                                                 str(e))
            LOG.audit('ActionExecution failed. ActionExecution=%s error=%s', actionexec_db, error)
            abort(http_client.INTERNAL_SERVER_ERROR, error)
            return
        else:
            actionexec_status = ACTIONEXEC_STATUS_SCHEDULED
            actionexec_db = update_actionexecution_status(actionexec_status,
                                                          actionexec_id=actionexec_id)
            self._kickoff_live_actions()
            actionexec_api = ActionExecutionAPI.from_model(actionexec_db)
            LOG.debug('POST /actionexecutions/ client_result=%s', actionexec_api)
            return actionexec_api

    @jsexpose(str, body=ActionExecutionAPI)
    def put(self, id, actionexecution):
        actionexecution.start_timestamp = datetime.datetime.now()
        actionexec_db = ActionExecutionsController.__get_by_id(id)
        new_actionexec_db = ActionExecutionAPI.to_model(actionexecution)
        if actionexec_db.status != new_actionexec_db.status:
            actionexec_db.status = new_actionexec_db.status
        if actionexec_db.result != new_actionexec_db.result:
            actionexec_db.result = new_actionexec_db.result
        actionexec_db = ActionExecution.add_or_update(actionexec_db)
        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)
        return actionexec_api

    def _kickoff_live_actions(self):
        if self._live_actions_pool.free() <= 0:
            return
        while not self._live_actions.empty() and self._live_actions_pool.free() > 0:
            action_exec_id = self._live_actions.get_nowait()
            self._live_actions_pool.spawn(self._issue_liveaction_post, action_exec_id)

    def _drain_live_actions(self):
        while True:
            while self._live_actions.empty():
                eventlet.greenthread.sleep(self._monitor_thread_empty_q_sleep_time)
            while self._live_actions_pool.free() <= 0:
                eventlet.greenthread.sleep(self._monitor_thread_no_workers_sleep_time)
            self._kickoff_live_actions()
