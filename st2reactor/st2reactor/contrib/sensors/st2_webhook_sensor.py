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

from functools import wraps
import os
import six

from flask import (jsonify, request, Flask)
import flask_jsonschema
from oslo.config import cfg
from st2common import log as logging
from st2common.models.system.common import ResourceReference, InvalidResourceReferenceError

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)
HOST = cfg.CONF.st2_webhook_sensor.host
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
            return jsonify({'error': msg}), http_client.BAD_REQUEST
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
        data = {'error': str(e)}
        js = jsonify(data)
        return js, http_client.BAD_REQUEST

    def __init__(self, container_service):
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)
        self._host = HOST
        self._port = PORT

    def setup(self):
        self._setup_flask_app()

    def start(self):
        St2WebhookSensor._app.run(port=self._port, host=self._host)

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
            self._log.exception('Exception %s handling webhook', e)
            return jsonify({'invalid': str(e)}), http_client.BAD_REQUEST

        try:
            self._container_service.dispatch(trigger, payload)
        except Exception as e:
            self._log.exception('Exception %s handling webhook', e)
            status = http_client.INTERNAL_SERVER_ERROR
            return jsonify({'error': str(e)}), status

        return jsonify({}), http_client.ACCEPTED

    # Flask app specific stuff.
    def _setup_flask_app(self):
        St2WebhookSensor._app.add_url_rule(BASE_URL, 'st2webhooks', self._handle_webhook,
                                           methods=['POST'])

    def _to_trigger(self, body):
        trigger = body.get('trigger', '')
        trigger_ref = None
        try:
            trigger_ref = ResourceReference.from_string_reference(ref=trigger)
        except InvalidResourceReferenceError:
            LOG.debug('Unable to parse reference.', exc_info=True)

        return {
            'name': trigger_ref.name if trigger_ref else None,
            'pack': trigger_ref.pack if trigger_ref else None,
            'type': body.get('type', ''),
            'parameters': {}
        }, body['payload']
