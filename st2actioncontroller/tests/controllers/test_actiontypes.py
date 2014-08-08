from tests import FunctionalTest


class TestActionTypesController(FunctionalTest):

    def test_get_one(self):
        resp = self.app.get('/actiontypes')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0, '/actiontypes did not return correct actiontypes.')
        actiontype_id = TestActionTypesController.__get_actiontype_id(resp.json[0])
        resp = self.app.get('/actiontypes/%s' % actiontype_id)
        retrieved_id = TestActionTypesController.__get_actiontype_id(resp.json)
        self.assertEqual(resp.status_int, 200)
        self.assertEquals(retrieved_id, actiontype_id,
                          '/actiontypes returned incorrect actiontype.')

    def test_get_all(self):
        resp = self.app.get('/actiontypes')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0, '/actiontypes did not return correct actiontypes.')

    def test_get_one_fail(self):
        resp = self.app.get('/actiontype/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @staticmethod
    def __get_actiontype_id(resp_json):
        return resp_json['id']
