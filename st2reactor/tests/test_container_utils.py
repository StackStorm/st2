import mock

from st2common.persistence.reactor import Trigger, TriggerType
from st2common.models.db.reactor import TriggerDB, TriggerTypeDB
from st2common.transport.publishers import PoolPublisher
import st2reactor.container.utils as container_utils
from st2tests.base import DbTestCase

MOCK_TRIGGER_TYPE = TriggerTypeDB()
MOCK_TRIGGER_TYPE.id = 'trigger-type-test.id'
MOCK_TRIGGER_TYPE.name = 'trigger-type-test.name'
MOCK_TRIGGER_TYPE.content_pack = 'dummy_pack_1'
MOCK_TRIGGER_TYPE.parameters_schema = {}
MOCK_TRIGGER_TYPE.payload_info = {}

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'
MOCK_TRIGGER.content_pack = 'dummy_pack_1'
MOCK_TRIGGER.parameters = {}
MOCK_TRIGGER.type = 'dummy_pack_1.trigger-type-test.name'


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ContainerUtilsTest(DbTestCase):
    @mock.patch.object(TriggerType, 'query', mock.MagicMock(
        return_value=[MOCK_TRIGGER_TYPE]))
    @mock.patch.object(Trigger, 'get_by_name', mock.MagicMock(return_value=MOCK_TRIGGER))
    @mock.patch.object(TriggerType, 'add_or_update')
    def test_add_trigger(self, mock_add_handler):
        mock_add_handler.return_value = MOCK_TRIGGER_TYPE
        container_utils.add_trigger_models(content_pack='dummy_pack_1',
                                           trigger_types=[MOCK_TRIGGER_TYPE])
        self.assertTrue(mock_add_handler.called, 'trigger not added.')

    def test_add_trigger_type(self):
        """
        This sensor has misconfigured trigger type. We shouldn't explode.
        """
        class FailTestSensor(object):
            started = False

            def setup(self):
                pass

            def start(self):
                FailTestSensor.started = True

            def stop(self):
                pass

            def get_trigger_types(self):
                return [
                    {'description': 'Ain\'t got no name'}
                ]

        try:
            container_utils.add_trigger_models(FailTestSensor().get_trigger_types())
            self.assertTrue(False, 'Trigger type doesn\'t have \'name\' field. Should have thrown.')
        except Exception:
            self.assertTrue(True)

    def test_create_trigger_instance_invalid_trigger(self):
        trigger_instance = {'name': 'footrigger', 'content_pack': 'dummy_pack'}
        instance = container_utils.create_trigger_instance(trigger_instance, {}, None)
        self.assertTrue(instance is None)

    def test_add_trigger_type_no_params(self):
        # Trigger type with no params should create a trigger with same name as trigger type.
        trig_type = {
            'name': 'myawesometriggertype',
            'content_pack': 'dummy_pack_1',
            'description': 'Words cannot describe how awesome I am.',
            'parameters_schema': {},
            'payload_schema': {}
        }
        trigtype_dbs = container_utils.add_trigger_models(content_pack='my_pack_1',
                                                          trigger_types=[trig_type])
        trigger_type, trigger = trigtype_dbs[0]

        trigtype_db = TriggerType.get_by_id(trigger_type.id)
        self.assertEqual(trigtype_db.content_pack, 'my_pack_1')
        self.assertEqual(trigtype_db.name, trig_type.get('name'))
        self.assertTrue(trigger is not None)
        self.assertEqual(trigger.name, trigtype_db.name)

    def test_add_trigger_type_with_params(self):
        MOCK_TRIGGER.type = 'system.test'
        # Trigger type with params should not create a trigger.
        PARAMETERS_SCHEMA = {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ['url'],
            "additionalProperties": False
        }
        trig_type = {
            'name': 'myawesometriggertype2',
            'content_pack': 'dummy_pack_1',
            'description': 'Words cannot describe how awesome I am.',
            'parameters_schema': PARAMETERS_SCHEMA,
            'payload_schema': {}
        }
        trigtype_dbs = container_utils.add_trigger_models(content_pack='my_pack_1',
                                                          trigger_types=[trig_type])
        trigger_type, trigger = trigtype_dbs[0]

        trigtype_db = TriggerType.get_by_id(trigger_type.id)
        self.assertEqual(trigtype_db.content_pack, 'my_pack_1')
        self.assertEqual(trigtype_db.name, trig_type.get('name'))
        self.assertEqual(trigger, None)
