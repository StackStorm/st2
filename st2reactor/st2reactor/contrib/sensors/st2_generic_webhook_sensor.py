from functools import wraps
import httplib
import os
from urlparse import urljoin

from flask import (jsonify, request, Flask)
import yaml

BASE_URL = '/webhooks/generic/'

PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string"}
    },
    "required": ['url'],
    "additionalProperties": False
}


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


class St2GenericWebhooksSensor(object):
    def __init__(self, container_service):
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)
        self._port = 6001
        self._app = Flask(__name__)
        # dirname, filename = os.path.split(os.path.abspath(__file__))
        # self._config_file = os.path.join(dirname, __name__ + '.yaml')
        # if not os.path.exists(self._config_file):
        #     raise Exception('Config file %s not found.' % self._config_file)
        # self._config = None

    def setup(self):
        # with open(self._config_file) as f:
        #     self._config = yaml.safe_load(f)
        #     self._setup_flask_app(urls=self._config.get('urls', []))
        pass

    def start(self):
        self._app.run(port=self._port)

    def stop(self):
        # If Flask is using the default Werkzeug server, then call shutdown on it.
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    def add(self, trigger):
        @validate_json
        def _handle_webhook():
            webhook_body = request.get_json()

            try:
                self._container_service.dispatch(trigger, webhook_body)
            except Exception as e:
                self._log.exception('Exception %s handling webhook', e)
                return jsonify({'error': str(e)}), httplib.INTERNAL_SERVER_ERROR

            # From rfc2616 sec 10.2.3 202 Accepted
            # "The entity returned with this response SHOULD include an indication of the request's
            # current status and either a pointer to a status monitor or some estimate of when the
            # user can expect the request to be fulfilled."
            return jsonify({}), httplib.ACCEPTED

        url = trigger['parameters']['url']
        full_url = urljoin(BASE_URL, url)
        self._log.info('Listening to endpoint: %s', full_url)
        self._app.add_url_rule(full_url, 'generic-webhook-' + url, _handle_webhook,
                               methods=['POST'])

    def get_trigger_types(self):
        return [{
            'name': 'st2.webhook',
            'payload_info': (),
            'parameters_schema': PARAMETERS_SCHEMA
        }]
