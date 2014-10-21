import six
from tests import FunctionalTest

http_client = six.moves.http_client


# TODO: Update tests once we include POST and PUT functionality
class SensorTypeControllerTestCase(FunctionalTest):
    def test_get_all(self):
        resp = self.app.get('/sensortypes')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 0)

    def test_get_one_doesnt_exist(self):
        resp = self.app.get('/sensortypes/1', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)
