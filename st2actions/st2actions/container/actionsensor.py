import eventlet
import json
import requests
import requests.exceptions

from oslo.config import cfg
from st2common import log as logging

ACTION_SENSOR_ENABLED = cfg.CONF.action_sensor.enable
TRIGGER_TYPE_ENDPOINT = cfg.CONF.action_sensor.triggers_base_url
TRIGGER_INSTANCE_ENDPOINT = cfg.CONF.action_sensor.webhook_sensor_base_url
TIMEOUT = cfg.CONF.action_sensor.request_timeout
MAX_ATTEMPTS = cfg.CONF.action_sensor.max_attempts
RETRY_WAIT = cfg.CONF.action_sensor.retry_wait
HTTP_POST_HEADER = {'content-type': 'application/json'}

LOG = logging.getLogger(__name__)

ACTION_TRIGGER_TYPE = {
    'name': 'st2.generic.actiontrigger',
    'description': 'Trigger encapsulating the completion of an action execution.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'execution_id': {},
            'status': {},
            'start_timestamp': {},
            'action_name': {},
            'parameters': {},
            'result': {}
        }
    }
}


def _do_register_trigger_type(attempt_no=0):
    LOG.debug('Attempt no %s to register %s.', attempt_no, ACTION_TRIGGER_TYPE['name'])
    try:
        payload = json.dumps(ACTION_TRIGGER_TYPE)
        r = requests.post(TRIGGER_TYPE_ENDPOINT,
                          data=payload,
                          headers=HTTP_POST_HEADER,
                          timeout=TIMEOUT)
        if r.status_code == 201:
            LOG.info('Registered trigger %s.', ACTION_TRIGGER_TYPE['name'])
        elif r.status_code == 409:
            LOG.info('Trigger %s is already registered.', ACTION_TRIGGER_TYPE['name'])
        else:
            LOG.error('Seeing status code %s on an attempt to register trigger %s.',
                      r.status_code, ACTION_TRIGGER_TYPE['name'])
    except requests.exceptions.ConnectionError:
        if attempt_no < MAX_ATTEMPTS:
            retry_wait = RETRY_WAIT * (attempt_no + 1)
            LOG.debug('    ConnectionError. Will retry in %ss.', retry_wait)
            eventlet.spawn_after(retry_wait, _do_register_trigger_type, attempt_no + 1)
        else:
            LOG.warn('Failed to register trigger %s. Exceeded max attempts to register trigger.',
                     ACTION_TRIGGER_TYPE['name'])
    except:
        LOG.exception('Failed to register trigger %s.', ACTION_TRIGGER_TYPE['name'])


def register_trigger_type():
    if not ACTION_SENSOR_ENABLED:
        return
    # spawn a thread to process this in order to unblock the main thread which at this point could
    # be in the middle of bootstraping the process.
    eventlet.greenthread.spawn(_do_register_trigger_type)


def post_trigger(action_execution):
    if not ACTION_SENSOR_ENABLED:
        return
    try:
        payload = json.dumps({
            'type': ACTION_TRIGGER_TYPE['name'],
            'payload': {
                'execution_id': str(action_execution.id),
                'status': action_execution.status,
                'start_timestamp': str(action_execution.start_timestamp),
                'action_name': action_execution.action['name'],
                'parameters': action_execution.parameters,
                'result': action_execution.result
            }
        })
        LOG.debug('POSTing %s for %s.', ACTION_TRIGGER_TYPE['name'], action_execution.id)
        r = requests.post(TRIGGER_INSTANCE_ENDPOINT,
                          data=payload,
                          headers=HTTP_POST_HEADER,
                          timeout=TIMEOUT)
    except:
        LOG.exception('Failed to fire trigger for action_execution %s.', str(action_execution.id))
    else:
        if r.status_code in [200, 201, 202]:
            LOG.debug('POSTed actionexecution %s as a trigger.', action_execution.id)
        else:
            LOG.warn('Seeing status code %s on an attempt to post triggerinstance for %s.',
                     r.status_code, action_execution.id)

register_trigger_type()
