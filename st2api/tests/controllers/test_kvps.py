from tests import FunctionalTest

KVP = {
    'name': 'keystone_endpoint',
    'value': 'http://localhost:5000/v3'
}


class TestKeyValuePairController(FunctionalTest):

    def test_get_all(self):
        resp = self.app.get('/keys')
        self.assertEqual(resp.status_int, 200)

    def test_get_one(self):
        post_resp = self.__do_post(KVP)
        kvp_id = self.__get_kvp_id(post_resp)
        get_resp = self.__do_get_one(kvp_id)
        self.assertEquals(get_resp.status_int, 200)
        self.assertEquals(self.__get_kvp_id(get_resp), kvp_id)
        self.__do_delete(kvp_id)

    def test_get_one_fail(self):
        resp = self.app.get('/keys/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_post_delete(self):
        post_resp = self.__do_post(KVP)
        self.assertEquals(post_resp.status_int, 201)
        self.__do_delete(self.__get_kvp_id(post_resp))

    def test_put(self):
        post_resp = self.__do_post(KVP)
        update_input = post_resp.json
        update_input['value'] = 'http://localhost:35357/v3'
        put_resp = self.__do_put(self.__get_kvp_id(post_resp), update_input)
        self.assertEquals(put_resp.status_int, 200)
        self.__do_delete(self.__get_kvp_id(put_resp))

    def test_put_fail(self):
        post_resp = self.__do_post(KVP)
        update_input = post_resp.json
        put_resp = self.__do_put(1, update_input, expect_errors=True)
        self.assertEquals(put_resp.status_int, 404)
        self.__do_delete(self.__get_kvp_id(post_resp))

    def test_delete(self):
        post_resp = self.__do_post(KVP)
        del_resp = self.__do_delete(self.__get_kvp_id(post_resp))
        self.assertEquals(del_resp.status_int, 204)

    @staticmethod
    def __get_kvp_id(resp):
        return resp.json['id']

    def __do_get_one(self, kvp_id, expect_errors=False):
        return self.app.get('/keys/%s' % kvp_id, expect_errors=expect_errors)

    def __do_post(self, kvp, expect_errors=False):
        return self.app.post_json('/keys', kvp, expect_errors=expect_errors)

    def __do_put(self, kvp_id, kvp, expect_errors=False):
        return self.app.put_json('/keys/%s' % kvp_id, kvp, expect_errors=expect_errors)

    def __do_delete(self, kvp_id, expect_errors=False):
        return self.app.delete('/keys/%s' % kvp_id, expect_errors=expect_errors)
