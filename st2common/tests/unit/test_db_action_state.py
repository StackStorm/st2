import bson

from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.persistence.executionstate import ActionExecutionState
from st2common.exceptions.db import StackStormDBObjectNotFoundError

from st2tests import DbTestCase


class ActionExecutionStateTests(DbTestCase):
    def test_state_crud(self):
        saved = ActionExecutionStateTests._create_save_actionstate()
        retrieved = ActionExecutionState.get_by_id(saved.id)
        self.assertDictEqual(saved.query_context, retrieved.query_context)
        self.assertEqual(saved.query_module, retrieved.query_module)
        ActionExecutionStateTests._delete(model_objects=[retrieved])
        try:
            retrieved = ActionExecutionState.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    @staticmethod
    def _create_save_actionstate():
        created = ActionExecutionStateDB()
        created.query_context = {'id': 'some_external_service_id'}
        created.query_module = 'dummy.modules.query1'
        created.execution_id = bson.ObjectId()
        return ActionExecutionState.add_or_update(created)

    @staticmethod
    def _delete(model_objects=[]):
        for model_object in model_objects:
            model_object.delete()
