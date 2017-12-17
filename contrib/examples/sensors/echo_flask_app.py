from flask import request, Flask

from st2reactor.sensor.base import Sensor


class EchoFlaskSensor(Sensor):
    def __init__(self, sensor_service, config):
        super(EchoFlaskSensor, self).__init__(
            sensor_service=sensor_service,
            config=config
        )

        self._host = '127.0.0.1'
        self._port = 5000
        self._path = '/echo'

        self._log = self._sensor_service.get_logger(__name__)
        self._app = Flask(__name__)

    def setup(self):
        pass

    def run(self):
        @self._app.route(self._path, methods=['POST'])
        def echo():
            payload = request.get_json(force=True)
            self._sensor_service.dispatch(trigger="examples.echo_flask",
                                          payload=payload)
            return request.data

        self._log.info('Listening for payload on http://{}:{}{}'.format(
            self._host, self._port, self._path))
        self._app.run(host=self._host, port=self._port, threaded=True)

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
