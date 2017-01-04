import mock
import unittest2

from oslo_config import cfg

from st2reactor.container.sensor_wrapper import SensorService

# This trigger has schema that uses all property types
TEST_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'age': {'type': 'integer'},
        'name': {'type': 'string', 'required': True},
        'address': {'type': 'string', 'default': '-'},
        'career': {'type': 'array'},
        'married': {'type': 'boolean'},
        'awards': {'type': 'object'},
        'income': {'anyOf': [{'type': 'integer'}, {'type': 'string'}]},
    },
}


class TriggerTypeMock(object):
    def __init__(self, schema={}):
        self.payload_schema = schema


class SensorServiceTestCase(unittest2.TestCase):
    def setUp(self):
        def side_effect(trigger, payload, trace_context):
            self._dispatched_count += 1

        self.sensor_service = SensorService(mock.MagicMock())
        self.sensor_service._dispatcher = mock.Mock()
        self.sensor_service._dispatcher.dispatch = mock.MagicMock(side_effect=side_effect)
        self._dispatched_count = 0

        # reset default configuration value
        cfg.CONF.sensorcontainer.permit_invalid_payload = True

    @mock.patch('st2common.services.triggers.get_trigger_type_db',
                mock.MagicMock(return_value=TriggerTypeMock(TEST_SCHEMA)))
    def test_dispatch_success(self):
        # define a valid payload
        payload = {
            'name': 'John Doe',
            'age': 25,
            'career': ['foo, Inc.', 'bar, Inc.'],
            'married': True,
            'awards': {'2016': ['hoge prize', 'fuga prize']},
            'income': 50000,
            'country': 'US',
        }

        # dispatching a trigger
        self.sensor_service.dispatch('trigger-name', payload)

        # This assumed that the target tirgger dispatched
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch('st2common.services.triggers.get_trigger_type_db',
                mock.MagicMock(return_value=TriggerTypeMock(TEST_SCHEMA)))
    def test_dispatch_failure_caused_by_incorrect_type(self):
        # define a invalid payload (the type of 'age' is incorrect)
        payload = {
            'name': 'John Doe',
            'age': '25',
        }

        # set config to stop dispatching when the payload comply with target trigger_type
        cfg.CONF.sensorcontainer.permit_invalid_payload = False

        self.sensor_service.dispatch('trigger-name', payload)

        # This assumed that the target tirgger doesn't dispatched
        self.assertEqual(self._dispatched_count, 0)

    @mock.patch('st2common.services.triggers.get_trigger_type_db',
                mock.MagicMock(return_value=TriggerTypeMock(TEST_SCHEMA)))
    def test_dispatch_failure_caused_by_lack_of_parameter(self):
        # define a invalid payload (lack of required property)
        payload = {
            'age': 25,
        }
        cfg.CONF.sensorcontainer.permit_invalid_payload = False

        self.sensor_service.dispatch('trigger-name', payload)
        self.assertEqual(self._dispatched_count, 0)

        # reset config to permit force dispatching
        cfg.CONF.sensorcontainer.permit_invalid_payload = True

        self.sensor_service.dispatch('trigger-name', payload)
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch('st2common.services.triggers.get_trigger_type_db',
                mock.MagicMock(return_value=TriggerTypeMock(TEST_SCHEMA)))
    def test_dispatch_failure_caused_by_too_much_parameter(self):
        # define a invalid payload ('hobby' is extra)
        payload = {
            'name': 'John Doe',
            'hobby': 'programming',
        }
        cfg.CONF.sensorcontainer.permit_invalid_payload = False

        self.sensor_service.dispatch('trigger-name', payload)
        self.assertEqual(self._dispatched_count, 0)

    @mock.patch('st2common.services.triggers.get_trigger_type_db',
                mock.MagicMock(return_value=TriggerTypeMock(TEST_SCHEMA)))
    def test_dispatch_success_with_multiple_type_value(self):
        payload = {
            'name': 'John Doe',
            'income': 1234,
        }

        cfg.CONF.sensorcontainer.permit_invalid_payload = False

        self.sensor_service.dispatch('trigger-name', payload)

        # reset payload which can have different type
        payload['income'] = 'secret'

        self.sensor_service.dispatch('trigger-name', payload)
        self.assertEqual(self._dispatched_count, 2)

    @mock.patch('st2common.services.triggers.get_trigger_type_db',
                mock.MagicMock(return_value=TriggerTypeMock(TEST_SCHEMA)))
    def test_dispatch_success_with_null(self):
        payload = {
            'name': 'John Doe',
            'age': None,
        }

        cfg.CONF.sensorcontainer.permit_invalid_payload = False

        self.sensor_service.dispatch('trigger-name', payload)
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch('st2common.services.triggers.get_trigger_type_db',
                mock.MagicMock(return_value=TriggerTypeMock()))
    def test_dispatch_success_without_payload_schema(self):
        # the case trigger has no property
        self.sensor_service.dispatch('trigger-name', {})
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch('st2common.services.triggers.get_trigger_type_db',
                mock.MagicMock(return_value=None))
    def test_dispatch_success_without_trigger_type(self):
        self.sensor_service.dispatch('trigger-name', {})
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch('st2common.services.triggers.get_trigger_type_db',
                mock.MagicMock(return_value=None))
    def test_dispatch_failure_without_trigger_ref(self):
        cfg.CONF.sensorcontainer.permit_invalid_payload = False

        self.sensor_service.dispatch('', {})
        self.assertEqual(self._dispatched_count, 0)
