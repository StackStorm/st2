from st2common.persistence.reactor import Trigger
from st2common.models.db import reactor
from tests import FunctionalTest

TRIGGER = reactor.TriggerDB()
TRIGGER.name = 'st2.test.trigger1'
TRIGGER.description = ''
TRIGGER.payload_info = ['tp1', 'tp2', 'tp3']
TRIGGER.trigger_source = None


class TestTriggerController(FunctionalTest):

    def setUp(self):
        # assigning id to none guarantees that it is assigned a new id before evey test.
        TRIGGER.id = None
        Trigger.add_or_update(TRIGGER)

    def tearDown(self):
        Trigger.delete(TRIGGER)

    def test_get_all(self):
        resp = self.app.get('/triggers')
        self.assertEqual(resp.status_int, 200)

    def test_get_one(self):
        resp = self.app.get('/triggers')
        trigger_id = resp.json[0]['id']
        get_one_resp = self.app.get('/triggers/%s' % trigger_id)
        self.assertEqual(get_one_resp.status_int, 200)