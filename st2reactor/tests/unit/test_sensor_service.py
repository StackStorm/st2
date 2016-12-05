import mock
import unittest2

from oslo_config import cfg

from st2reactor.container.sensor_wrapper import SensorService


class TriggerTypeMock(object):
    def __init__(self, schema={}):
        self.payload_schema = schema

# This trigger has schema that uses all property types
TRIGGER_TYPE_MOCK = TriggerTypeMock({
    'type': 'object',
    'properties': {
        'age': {'type': 'integer'},
        'name': {'type': 'string'},
        'address': {'type': 'string', 'default': '-'},
        'attributes': {
            'type': 'object',
            'properties': {
                'career': {'type': 'array'},
                'married': {'type': 'boolean'},
                'awards': {'type': 'object'},
                'income': {'anyOf': [{'type': 'integer'}, {'type': 'string'}]},
            },
        },
    },
})


@mock.patch('st2common.services.triggers.get_trigger_type_db',
            mock.MagicMock(return_value=TRIGGER_TYPE_MOCK))
class SensorServiceTestCase(unittest2.TestCase):
    def setUp(self):
        def side_effect(trigger, payload, trace_context):
            self._dispatched_count += 1

        self.sensor_service = SensorService(mock.MagicMock())
        self.sensor_service._dispatcher = mock.Mock()
        self.sensor_service._dispatcher.dispatch = mock.MagicMock(side_effect=side_effect)
        self._dispatched_count = 0

    def test_dispatch_success(self):
        # define a valid payload
        payload = {
            'name': 'John Doe',
            'age': 25,
            'attributes': {
                'career': ['foo, Inc.', 'bar, Inc.'],
                'married': True,
                'awards': {'hoge prize': 2016},
                'income': 50000,
            },
        }

        # dispatching a trigger
        self.sensor_service.dispatch('trigger-name', payload)

        # This assumed that the target tirgger dispatched
        self.assertEqual(self._dispatched_count, 1)

        # reset payload which can have different type
        payload['attributes']['income'] = 'secret'

        self.sensor_service.dispatch('trigger-name', payload)
        self.assertEqual(self._dispatched_count, 2)

    def test_dispatch_failure_caused_by_incorrect_type(self):
        # define a invalid payload (the type of 'age' is incorrect)
        payload = {
            'name': 'John Doe',
            'age': '25',
            'attributes': {
                'career': ['foo, Inc.', 'bar, Inc.'],
                'married': True,
                'awards': {'hoge prize': 2016},
                'income': 50000,
            },
        }

        # set config to stop dispatching when the payload comply with target trigger_type
        cfg.CONF.sensorcontainer.permit_invalid_payload = False

        self.sensor_service.dispatch('trigger-name', payload)

        # This assumed that the target tirgger doesn't dispatched
        self.assertEqual(self._dispatched_count, 0)

    def test_dispatch_failure_caused_by_lack_of_parameter(self):
        # define a invalid payload (lack of 'attributes' property)
        payload = {
            'name': 'John Doe',
            'age': 25,
        }
        cfg.CONF.sensorcontainer.permit_invalid_payload = False

        self.sensor_service.dispatch('trigger-name', payload)
        self.assertEqual(self._dispatched_count, 0)

        # reset config to permit force dispatching
        cfg.CONF.sensorcontainer.permit_invalid_payload = True

        self.sensor_service.dispatch('trigger-name', payload)
        self.assertEqual(self._dispatched_count, 1)

    def test_dispatch_failure_caused_by_too_much_parameter(self):
        # define a invalid payload ('hobby' is extra)
        payload = {
            'name': 'John Doe',
            'age': 25,
            'attributes': {
                'career': ['foo, Inc.', 'bar, Inc.'],
                'married': True,
                'awards': {'hoge prize': 2016},
                'income': 50000,
                'hobby': 'programming',
            },
        }
        cfg.CONF.sensorcontainer.permit_invalid_payload = False

        self.sensor_service.dispatch('trigger-name', payload)
        self.assertEqual(self._dispatched_count, 0)
