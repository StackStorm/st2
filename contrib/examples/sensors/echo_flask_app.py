# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from flask import request, jsonify, Flask

from st2reactor.sensor.base import Sensor


class EchoFlaskSensor(Sensor):
    def __init__(self, sensor_service, config):
        super(EchoFlaskSensor, self).__init__(
            sensor_service=sensor_service, config=config
        )

        self._host = "127.0.0.1"
        self._port = 5000
        self._path = "/echo"

        self._log = self._sensor_service.get_logger(__name__)
        self._app = Flask(__name__)

    def setup(self):
        pass

    def run(self):
        @self._app.route(self._path, methods=["POST"])
        def echo():
            payload = request.get_json(force=True)
            self._sensor_service.dispatch(
                trigger="examples.echoflasksensor", payload=payload
            )
            return jsonify(
                request.get_json(force=True), status=200, mimetype="application/json"
            )

        self._log.info(
            "Listening for payload on http://{}:{}{}".format(
                self._host, self._port, self._path
            )
        )
        self._app.run(host=self._host, port=self._port, threaded=False)

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        # This method is called when trigger is created
        pass

    def update_trigger(self, trigger):
        # This method is called when trigger is updated
        pass

    def remove_trigger(self, trigger):
        # This method is called when trigger is deleted
        pass
