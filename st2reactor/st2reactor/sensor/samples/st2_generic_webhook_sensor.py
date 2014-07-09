from functools import wraps
import httplib
import os

from flask import (jsonify, request, Flask)
import yaml

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


class St2GenericWebhooksSensor(object):
    def __init__(self, container_service):
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)
        self._port = 6001
        self._app = Flask(__name__)
        dirname, filename = os.path.split(os.path.abspath(__file__))
        self._config_file = os.path.join(dirname, __name__ + '.yaml')
        if not os.path.exists(self._config_file):
            raise Exception('Config file %s not found.' % self._config_file)
        self._config = None

    def setup(self):
        with open(self._config_file) as f:
            self._config = yaml.safe_load(f)
            self._setup_flask_app(urls=self._config.get('urls', []))

    def start(self):
        self._app.run(port=self._port)

    def stop(self):
        # If Flask is using the default Werkzeug server, then call shutdown on it.
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    def get_trigger_types(self):
        return []

    @validate_json
    def _handle_webhook(self, name):
        webhook_body = request.get_json()
        # Generate trigger instances and send them.
        triggers = self._to_triggers(webhook_body)

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
    def _setup_flask_app(self, urls=[]):
        for url in urls:
            self._app.add_url_rule('/webhooks/generic/<path:name>',
                                   'generic-webhook-' + url,
                                   self._handle_webhook, methods=['POST'])

    def _to_triggers(self, webhook_body):
        triggers = []

        # XXX: if there is schema mismatch among entries, we ignore.
        for item in webhook_body:
            triggers.append(item)

        return triggers
