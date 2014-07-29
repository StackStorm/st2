import os
import logging
import unittest2

from st2client.client import Client


LOG = logging.getLogger(__name__)


class TestClientEndpoints(unittest2.TestCase):

    def tearDown(self):
        for var in ['ST2_BASE_URL', 'ST2_ACTION_URL',
                    'ST2_REACTOR_URL', 'ST2_DATASTORE_URL']:
            if var in os.environ:
                del os.environ[var]

    def test_default(self):
        base_url = 'http://localhost'
        action_url = 'http://localhost:9101'
        reactor_url = 'http://localhost:9102'
        datastore_url = 'http://localhost:9103'

        client = Client()
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['action'], action_url)
        self.assertEqual(endpoints['reactor'], reactor_url)
        self.assertEqual(endpoints['datastore'], datastore_url)

    def test_env(self):
        base_url = 'http://www.stackstorm.com'
        action_url = 'http://www.st2.com:9101'
        reactor_url = 'http://www.st2.com:9102'
        datastore_url = 'http://www.st2.com:9103'

        os.environ['ST2_BASE_URL'] = base_url
        os.environ['ST2_ACTION_URL'] = action_url
        os.environ['ST2_REACTOR_URL'] = reactor_url
        os.environ['ST2_DATASTORE_URL'] = datastore_url
        self.assertEqual(os.environ.get('ST2_BASE_URL'), base_url)
        self.assertEqual(os.environ.get('ST2_ACTION_URL'), action_url)
        self.assertEqual(os.environ.get('ST2_REACTOR_URL'), reactor_url)
        self.assertEqual(os.environ.get('ST2_DATASTORE_URL'), datastore_url)

        client = Client()
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['action'], action_url)
        self.assertEqual(endpoints['reactor'], reactor_url)
        self.assertEqual(endpoints['datastore'], datastore_url)

    def test_env_base_only(self):
        base_url = 'http://www.stackstorm.com'
        action_url = 'http://www.stackstorm.com:9101'
        reactor_url = 'http://www.stackstorm.com:9102'
        datastore_url = 'http://www.stackstorm.com:9103'

        os.environ['ST2_BASE_URL'] = base_url
        self.assertEqual(os.environ.get('ST2_BASE_URL'), base_url)
        self.assertEqual(os.environ.get('ST2_ACTION_URL'), None)
        self.assertEqual(os.environ.get('ST2_REACTOR_URL'), None)
        self.assertEqual(os.environ.get('ST2_DATASTORE_URL'), None)

        client = Client()
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['action'], action_url)
        self.assertEqual(endpoints['reactor'], reactor_url)
        self.assertEqual(endpoints['datastore'], datastore_url)

    def test_args(self):
        base_url = 'http://www.stackstorm.com'
        action_url = 'http://www.st2.com:9101'
        reactor_url = 'http://www.st2.com:9102'
        datastore_url = 'http://www.st2.com:9103'

        client = Client(base_url=base_url, action_url=action_url,
                        reactor_url=reactor_url, datastore_url=datastore_url)
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['action'], action_url)
        self.assertEqual(endpoints['reactor'], reactor_url)
        self.assertEqual(endpoints['datastore'], datastore_url)

    def test_args_base_only(self):
        base_url = 'http://www.stackstorm.com'
        action_url = 'http://www.stackstorm.com:9101'
        reactor_url = 'http://www.stackstorm.com:9102'
        datastore_url = 'http://www.stackstorm.com:9103'

        client = Client(base_url=base_url)
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['action'], action_url)
        self.assertEqual(endpoints['reactor'], reactor_url)
        self.assertEqual(endpoints['datastore'], datastore_url)
