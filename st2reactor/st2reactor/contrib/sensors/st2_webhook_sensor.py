from functools import wraps
import httplib
import os

from flask import (jsonify, request, Flask)
import flask_jsonschema
from oslo.config import cfg

PORT = cfg.CONF.st2_webhook_sensor.port
BASE_URL = cfg.CONF.st2_webhook_sensor.url


# Dectorators for request validations.
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


class St2WebhookSensor(object):
    '''
    A webhook sensor using a micro-framework Flask.
    '''

    # Flask specific stuff.
    _app = Flask('st2_webhook_sensor')
    _app.config['JSONSCHEMA_DIR'] = os.path.join(_app.root_path, 'st2webhookschemas')

    jsonschema = flask_jsonschema.JsonSchema(_app)

    @_app.errorhandler(flask_jsonschema.ValidationError)
    def on_validation_error(e):
        data = {'error': e.message}
        js = jsonify(data)
        return js, httplib.BAD_REQUEST

    def __init__(self, container_service):
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)
        self._port = PORT

    def setup(self):
        self._setup_flask_app()

    def start(self):
        St2WebhookSensor._app.run(port=self._port)

    def stop(self):
        # If Flask is using the default Werkzeug server, then call shutdown on it.
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def get_trigger_types(self):
        return []

    @validate_json
    @flask_jsonschema.validate('st2webhooks', 'create')
    def _handle_webhook(self):
        body = request.get_json()

        try:
            trigger, payload = self._to_trigger(body)
        except KeyError as e:
            return jsonify({'invalid': e}), httplib.BAD_REQUEST

        try:
            self._container_service.dispatch(trigger, payload)
        except Exception as e:
            self._log.exception('Exception %s handling webhook', e)
            status = httplib.INTERNAL_SERVER_ERROR
            return jsonify({'error': str(e)}), status

        return jsonify({}), httplib.ACCEPTED

    # Flask app specific stuff.
    def _setup_flask_app(self):
        St2WebhookSensor._app.add_url_rule(BASE_URL, 'st2webhooks', self._handle_webhook,
                                           methods=['POST'])

    def _to_trigger(self, body):
        return {
            'name': body.get('name', ''),
            'type': {
                'name': body['type']
            },
            'parameters': {}
        }, body['payload']
