import tests
import unittest2
import mongoengine.connection
from oslo.config import cfg
from st2common.models.db import setup, teardown


class DbConnectionTest(unittest2.TestCase):
    def setUp(self):
        tests.parse_args()
        setup()

    def tearDown(self):
        teardown()

    def test_check_connect(self):
        client = mongoengine.connection.get_connection()
        self.assertEqual(client.host, cfg.CONF.database.host,
                         'Not connected to desired host.')
        self.assertEqual(client.port, cfg.CONF.database.port,
                         'Not connected to desired port.')
