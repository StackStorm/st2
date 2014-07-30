import httplib
import unittest2
from st2common.persistence.reactor import Trigger
from st2common.models.db import reactor
from tests import FunctionalTest

TRIGGER_0 = {
    'name': 'st2.test.trigger0',
    'description': 'test trigger',
    'payload_schema': {
        'type': 'object'
    }
}
TRIGGER_1 = {
    'name': 'st2.test.trigger1',
    'description': 'test trigger',
    'payload_schema': {
        'type': 'object'
    }
}


class TestTriggerController(FunctionalTest):

    def test_get_all(self):
        post_resp = self.__do_post(TRIGGER_0)
        trigger_id_0 = self.__get_trigger_id(post_resp)
        post_resp = self.__do_post(TRIGGER_1)
        trigger_id_1 = self.__get_trigger_id(post_resp)
        resp = self.app.get('/triggers')
        self.assertEqual(resp.status_int, httplib.OK)
        self.assertEqual(len(resp.json), 2, 'Get all failure.')
        self.__do_delete(trigger_id_0)
        self.__do_delete(trigger_id_1)

    def test_get_one(self):
        post_resp = self.__do_post(TRIGGER_1)
        trigger_id = self.__get_trigger_id(post_resp)
        get_resp = self.__do_get_one(trigger_id)
        self.assertEquals(get_resp.status_int, httplib.OK)
        self.assertEquals(self.__get_trigger_id(get_resp), trigger_id)
        self.__do_delete(trigger_id)

    def test_get_one_fail(self):
        resp = self.__do_get_one('1')
        self.assertEqual(resp.status_int, httplib.NOT_FOUND)

    def test_post(self):
        post_resp = self.__do_post(TRIGGER_1)
        self.assertEquals(post_resp.status_int, httplib.CREATED)
        self.__do_delete(self.__get_trigger_id(post_resp))

    @unittest2.skip('/triggers is accepting dups!')
    def test_post_duplicate(self):
        post_resp = self.__do_post(TRIGGER_1)
        self.assertEquals(post_resp.status_int, httplib.CREATED)
        post_resp_2 = self.__do_post(TRIGGER_1)
        self.assertEquals(post_resp_2.status_int, httplib.CONFLICT)
        self.__do_delete(self.__get_trigger_id(post_resp))

    def test_put(self):
        post_resp = self.__do_post(TRIGGER_1)
        update_input = post_resp.json
        update_input['description'] = 'updated description.'
        put_resp = self.__do_put(self.__get_trigger_id(post_resp), update_input)
        self.assertEquals(put_resp.status_int, httplib.OK)
        self.__do_delete(self.__get_trigger_id(put_resp))

    def test_put_fail(self):
        post_resp = self.__do_post(TRIGGER_1)
        update_input = post_resp.json
        # If the id in the URL is incorrect the update will fail since id in the body is ignored.
        put_resp = self.__do_put(1, update_input)
        self.assertEquals(put_resp.status_int, httplib.NOT_FOUND)
        self.__do_delete(self.__get_trigger_id(post_resp))

    def test_delete(self):
        post_resp = self.__do_post(TRIGGER_1)
        del_resp = self.__do_delete(self.__get_trigger_id(post_resp))
        self.assertEquals(del_resp.status_int, httplib.NO_CONTENT)

    @staticmethod
    def __get_trigger_id(resp):
        return resp.json['id']

    def __do_get_one(self, trigger_id):
        return self.app.get('/triggers/%s' % trigger_id, expect_errors=True)

    def __do_post(self, trigger):
        return self.app.post_json('/triggers', trigger, expect_errors=True)

    def __do_put(self, trigger_id, trigger):
        return self.app.put_json('/triggers/%s' % trigger_id, trigger, expect_errors=True)

    def __do_delete(self, trigger_id):
        return self.app.delete('/triggers/%s' % trigger_id)
