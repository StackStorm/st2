from tests import FunctionalTest


class TestRunnerTypesController(FunctionalTest):

    def test_get_one(self):
        resp = self.app.get('/runnertypes')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0, '/runnertypes did not return correct runnertypes.')
        runnertype_id = TestRunnerTypesController.__get_runnertype_id(resp.json[0])
        resp = self.app.get('/runnertypes/%s' % runnertype_id)
        retrieved_id = TestRunnerTypesController.__get_runnertype_id(resp.json)
        self.assertEqual(resp.status_int, 200)
        self.assertEquals(retrieved_id, runnertype_id,
                          '/runnertypes returned incorrect runnertype.')

    def test_get_all(self):
        resp = self.app.get('/runnertypes')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0, '/runnertypes did not return correct runnertypes.')

    def test_get_one_fail(self):
        resp = self.app.get('/runnertype/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @staticmethod
    def __get_runnertype_id(resp_json):
        return resp_json['id']
