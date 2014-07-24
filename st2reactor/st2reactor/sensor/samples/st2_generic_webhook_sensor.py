import jsonschema
import httplib
from pecan.rest import abort, expose, RestController
import wsmeext.pecan
import wsme.types

from mirantis.resource import Resource

from st2reactor.sensor.base import Sensor, SensorHook

'''
Dectorators for request validations.
'''


def _to_trigger(name, payload):
    return {'name': name, 'payload': payload}


class SensorInstanceAPI(Resource):
    name = wsme.types.text
    event_id = wsme.types.text
    config = wsme.types.DictType(str, str)

    # That's not right. It would validate the object produced by to_dict, not the one we are
    # actually getting (and it's already lost, converted to Resource by the time validation starts)
    @staticmethod
    def validate(value):
        jsonschema.validate(value.to_dict(), St2WebhookSensor.schema)
        return value

    def get_trigger_name(self):
        return self.event_id or 'generic-webhook-' + self.name

    def to_dict(self):
        return {
            'name': self.name,
            'event_id': self.event_id,
            'config': self.config
        }


class GenericHook(RestController):
    def __init__(self, sensor_instance, sensor):
        super(GenericHook, self).__init__()
        self._sensor_instance = sensor_instance
        self._sensor = sensor

    @wsmeext.pecan.wsexpose(SensorInstanceAPI)
    def get(self):
        """
            Get hook.

            Handles requests:
                GET /sensors/webhook/[name]
        """
        self._sensor._log.info('GET /sensors/%s/%s/',
                               self._sensor.webhook.name,
                               self._sensor_instance.name)

        sensor_instance = self._sensor_instance

        self._sensor._log.debug('GET /sensors/%s/%s/ client_result=%s',
                               self._sensor.webhook.name,
                               self._sensor_instance.name,
                               sensor_instance)
        return sensor_instance

    @wsmeext.pecan.wsexpose(wsme.types.text, body=wsme.types.text, status_code=httplib.ACCEPTED)
    def post(self, webhook_body):
        """
            Trigger a hook.

            Handles requests:
                POST /sensors/webhook/[name]
        """
        self._sensor._log.info('POST /sensors/%s/%s/ with rule data=%s',
                               self._sensor.webhook.name,
                               self._sensor_instance.name,
                               webhook_body)

        trigger_name = self._sensor_instance.get_trigger_name()
        if isinstance(webhook_body, dict):
            webhook_body = [webhook_body]

        # Validate

        triggers = (_to_trigger(trigger_name, hooks) for hooks in webhook_body)

        try:
            self._sensor._container_service.dispatch(triggers)
        except Exception as e:
            self._sensor._log.exception('Exception %s handling webhook', e)
            return abort(httplib.INTERNAL_SERVER_ERROR, str(e))

        self._sensor._log.debug('POST /sensors/%s/%s/ client_result=%s',
                               self._sensor.webhook.name,
                               self._sensor_instance.name,
                               webhook_body)
        return webhook_body


# For now, you have to keep base class here both because you need to check `name` is present, but
# also for pecan to figure out this is actually a controller (it needs to have `_route` method
# present somewhere in MRO and by replacing `_lookup` with `_route` we probably can work around this
# issue, but I'm not quite there yet)
class St2WebhookHook(SensorHook):
    name = 'webhook'

    @wsmeext.pecan.wsexpose([SensorInstanceAPI])
    def get_all(self):
        """
            List all hooks.

            Handles requests:
                GET /sensors/webhook/
        """
        self._sensor._log.info('GET all /sensors/%s/', self._sensor.webhook.name)
        sensor_instances = self._sensor._hooks.values()
        self._sensor._log.debug('GET all /sensors/%s/ client_result=%s',
                                self._sensor.webhook.name,
                                sensor_instances)
        return sensor_instances

    # This one is unreachable due to _lookup function being used and are left here only as an
    # example for sensors that not planing to use subcontrollers.
    # @wsme_pecan.wsexpose(SensorInstanceAPI, wstypes.text)
    def get_one(self, name):
        """
            List hook by name.

            Handle:
                GET /sensors/webhook/1
        """
        self._sensor._log.info('GET /sensors/webhook/ with id=%s', id)
        try:
            sensor_instance = self._sensor._hooks[name]
            self._sensor._log.debug('GET /sensors/webhook/ with id=%s, client_result=%s', id, sensor_instance)
            return sensor_instance
        except KeyError as e:
            self._sensor._log.debug('Instance lookup for name="%s" resulted in exception : %s.', name, e)
            return abort(httplib.NOT_FOUND)

    @wsmeext.pecan.wsexpose(SensorInstanceAPI, body=SensorInstanceAPI, status_code=httplib.CREATED)
    def post(self, sensor_instance):
        """
            Create a new hook.

            Handles requests:
                POST /sensors/webhook/
        """
        self._sensor._log.info('POST /sensors/%s/ with rule data=%s',
                               self._sensor.webhook.name,
                               sensor_instance)

        self._sensor.add_hook(sensor_instance)

        self._sensor._log.debug('POST /sensors/%s/ client_result=%s',
                                self._sensor.webhook.name,
                                sensor_instance)
        return sensor_instance

    @expose()
    def _lookup(self, primary_key, *remainder):
        if self._sensor.enabled:
            try:
                sensor_instance = self._sensor.get_hook(primary_key)
                return GenericHook(sensor_instance, self._sensor), remainder
            except KeyError:
                abort(httplib.NOT_FOUND)
        else:
            abort(httplib.FORBIDDEN, "Sensor is disabled")


class St2WebhookSensor(Sensor):
    """
    A webhook sensor.
    """

    schema = {
        "type": "object",
        "properties": {
            "name": {},
            "event_id": {},
            "config": {}
        },
        "required": ["name", "config"]
    }

    webhook = St2WebhookHook

    def __init__(self, container_service):
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)

        self.webhook._sensor = self
        self.webhook._container_service = container_service

        self._hooks = {}
        self.enabled = False

    def setup(self):
        # Probably read configs and create predefined sensor_instances
        pass

    def start(self):
        self.enabled = True

    def stop(self):
        self.enabled = False

    def add_hook(self, sensor_instance):
        trigger_name = sensor_instance.get_trigger_name()
        self._container_service.add_trigger_type(_to_trigger(trigger_name, sensor_instance.config))
        self._hooks[sensor_instance.name] = sensor_instance

    def get_hook(self, name):
        return self._hooks[name]