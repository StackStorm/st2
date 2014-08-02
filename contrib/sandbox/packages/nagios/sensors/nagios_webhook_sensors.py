from functools import wraps
import httplib
import os

from flask import (jsonify, request, Flask)
from flask_jsonschema import (JsonSchema, ValidationError)

'''
Dectorators for request validations.
'''


def validate_json(f):
    @wraps(f)
    def wrapper(*args, **kw):
        try:
            request.json
        except Exception:
            msg = 'Content-Type must be application/json.'
            return jsonify({'error': msg}), httplib.BAD_REQUEST
        return f(*args, **kw)
    return wrapper


class NagiosWebhookSensor(object):
    '''
    A webhook sensor using a micro-framework Flask.
    '''

    '''
    Flask specific stuff.
    '''
    _app = Flask('nagios_webhook_sensor')
    _app.config['JSONSCHEMA_DIR'] = os.path.join('/opt/stackstorm/repo/sensors/st2webhookschemas')
    _jsonschema = JsonSchema(_app)

    @_app.errorhandler(ValidationError)
    def on_validation_error(e):
        data = {'error': e.message}
        js = jsonify(data)
        return js, httplib.BAD_REQUEST

    def __init__(self, container_service):
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)
        self._port = 6002
        self._address = '0.0.0.0'

    def setup(self):
        self._setup_flask_app()

    def start(self):
        NagiosWebhookSensor._app.run(port=self._port,host=self._address)

    def stop(self):
        # If Flask is using the default Werkzeug server, then call shutdown on it.
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    def get_trigger_types(self):
        return [{'name': 'st2.nagios_service_state', 'description': 'Nagios Service State Change Sensor', 'payload_info': ['host', 'service', 'state', 'state_type', 'attempt', 'msg']}]

    @validate_json
    @_jsonschema.validate('st2webhooks', 'create')
    def _handle_webhook(self):
        webhook_body = request.get_json()
        # Generate trigger instances and send them.
        triggers, errors = self._to_triggers(webhook_body)
        if errors:
            return jsonify({'invalid': errors}), httplib.BAD_REQUEST

        try:
            self._container_service.dispatch(triggers)
        except Exception as e:
            self._log.exception('Exception %s handling webhook', e)
            status = httplib.INTERNAL_SERVER_ERROR
            return jsonify({'error': str(e)}), status

        return jsonify({}), httplib.ACCEPTED

    '''
    Flask app specific stuff.
    '''
    def _setup_flask_app(self):
        NagiosWebhookSensor._app.add_url_rule('/webhooks/nagios_service_state', 'st2webhooks', self._handle_webhook,
                                           methods=['POST'])

    def _to_triggers(self, webhook_body):
        triggers = []
        errors = []
        for obj in webhook_body:
            trigger = {}
            trigger['name'] = obj.get(u'name', '')

            if not trigger['name']:
                errors.append(obj)
                continue

            trigger['payload'] = obj.get(u'payload', {})
            event_id = obj.get(u'event_id')
            if event_id is not None:
                trigger['event_id'] = event_id
            triggers.append(trigger)

        return triggers, errors


