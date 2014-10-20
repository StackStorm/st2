import six
from tests import FunctionalTest

http_client = six.moves.http_client

TRIGGER_0 = {
    'name': 'st2.test.triggertype0',
    'content_pack': 'dummy_pack_1',
    'description': 'test trigger',
    'payload_schema': {'tp1': None, 'tp2': None, 'tp3': None},
    'parameters_schema': {}
}
TRIGGER_1 = {
    'name': 'st2.test.triggertype1',
    'content_pack': 'dummy_pack_2',
    'description': 'test trigger',
    'payload_schema': {'tp1': None, 'tp2': None, 'tp3': None},
}
TRIGGER_2 = {
    'name': 'st2.test.triggertype2',
    'content_pack': 'dummy_pack_3',
    'description': 'test trigger',
    'payload_schema': {'tp1': None, 'tp2': None, 'tp3': None},
    'parameters_schema': {'param1': {'type': 'object'}}
}


class TestTriggerTypeController(FunctionalTest):

    def test_get_all(self):
        post_resp = self.__do_post(TRIGGER_0)
        trigger_id_0 = self.__get_trigger_id(post_resp)
        post_resp = self.__do_post(TRIGGER_1)
        trigger_id_1 = self.__get_trigger_id(post_resp)
        resp = self.app.get('/triggertypes')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 2, 'Get all failure.')
        self.__do_delete(trigger_id_0)
        self.__do_delete(trigger_id_1)

    def test_get_one(self):
        post_resp = self.__do_post(TRIGGER_1)
        trigger_id = self.__get_trigger_id(post_resp)
        get_resp = self.__do_get_one(trigger_id)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.assertEqual(self.__get_trigger_id(get_resp), trigger_id)
        self.__do_delete(trigger_id)

    def test_get_one_fail(self):
        resp = self.__do_get_one('1')
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    def test_post(self):
        post_resp = self.__do_post(TRIGGER_1)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        self.__do_delete(self.__get_trigger_id(post_resp))

    def test_post_with_params(self):
        post_resp = self.__do_post(TRIGGER_2)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        self.__do_delete(self.__get_trigger_id(post_resp))

    def test_post_duplicate(self):
        post_resp = self.__do_post(TRIGGER_1)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        post_resp_2 = self.__do_post(TRIGGER_1)
        self.assertEqual(post_resp_2.status_int, http_client.CONFLICT)
        self.__do_delete(self.__get_trigger_id(post_resp))

    def test_put(self):
        post_resp = self.__do_post(TRIGGER_1)
        update_input = post_resp.json
        update_input['description'] = 'updated description.'
        put_resp = self.__do_put(self.__get_trigger_id(post_resp), update_input)
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.__do_delete(self.__get_trigger_id(put_resp))

    def test_put_fail(self):
        post_resp = self.__do_post(TRIGGER_1)
        update_input = post_resp.json
        # If the id in the URL is incorrect the update will fail since id in the body is ignored.
        put_resp = self.__do_put(1, update_input)
        self.assertEqual(put_resp.status_int, http_client.NOT_FOUND)
        self.__do_delete(self.__get_trigger_id(post_resp))

    def test_delete(self):
        post_resp = self.__do_post(TRIGGER_1)
        del_resp = self.__do_delete(self.__get_trigger_id(post_resp))
        self.assertEqual(del_resp.status_int, http_client.NO_CONTENT)

    @staticmethod
    def __get_trigger_id(resp):
        return resp.json['id']

    def __do_get_one(self, trigger_id):
        return self.app.get('/triggertypes/%s' % trigger_id, expect_errors=True)

    def __do_post(self, trigger):
        return self.app.post_json('/triggertypes', trigger, expect_errors=True)

    def __do_put(self, trigger_id, trigger):
        return self.app.put_json('/triggertypes/%s' % trigger_id, trigger, expect_errors=True)

    def __do_delete(self, trigger_id):
        return self.app.delete('/triggertypes/%s' % trigger_id)
