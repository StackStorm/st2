from functools import wraps
import httplib
import os

from flask import (jsonify, request, Flask)
from flask_jsonschema import (JsonSchema, ValidationError)

app = Flask(__name__)
app.config['JSONSCHEMA_DIR'] = os.path.join(app.root_path, 'st2webhookschemas')
jsonschema = JsonSchema(app)

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


@app.errorhandler(ValidationError)
def on_validation_error(e):
    data = {'error': e.message}
    js = jsonify(data)
    return js, httplib.BAD_REQUEST


class St2WebhookSensor(object):
    '''
    A webhook sensor using a micro-framework Flask.
    '''
    __container_service = None
    __log = None

    '''
    Flask specific stuff.
    '''
    __port = 6000

    def __init__(self, container_service):
        self.__container_service = container_service
        self.__log = self.__container_service.get_logger(self.__class__.__name__)

    def setup(self):
        self._setup_flask_app()

    def start(self):
        app.run(port=self.__port)

    def stop(self):
        # If Flask is using the default Werkzeug server, then call shutdown on it.
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    def get_trigger_types(self):
        return []

    '''
    Flask app specific stuff.
    '''
    def _setup_flask_app(self):
        @app.route('/webhooks/st2', methods=['POST'])
        @validate_json
        @jsonschema.validate('st2webhooks', 'create')
        def handle_webhook():
            webhook_body = request.get_json()
            data = {}
            status = httplib.ACCEPTED
            triggers = []
            trigger = {}
            trigger['name'] = webhook_body.get(u'name', '')

            if not trigger['name']:
                status = httplib.BAD_REQUEST
                data = {'error': '"name" field has to be non-empty.'}
                return jsonify(data), status

            trigger['payload'] = webhook_body.get(u'payload', {})
            event_id = webhook_body.get(u'event_id')
            if event_id is not None:
                trigger['event_id'] = event_id
            triggers.append(trigger)
            # Generate trigger instances and send them.
            try:
                self.__container_service.dispatch(triggers)
            except Exception as e:
                self.__log.exception('Exception %s handling webhook %s', e, trigger['name'])
                status = httplib.INTERNAL_SERVER_ERROR
                data = {'error': str(e)}

            return jsonify(data), status
