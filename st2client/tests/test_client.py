import os
import logging
import unittest2

from st2client.client import Client


LOG = logging.getLogger(__name__)


class TestClientEndpoints(unittest2.TestCase):

    def tearDown(self):
        for var in ['ST2_BASE_URL', 'ST2_API_URL', 'ST2_DATASTORE_URL']:
            if var in os.environ:
                del os.environ[var]

    def test_default(self):
        base_url = 'http://localhost'
        api_url = 'http://localhost:9101'
        datastore_url = 'http://localhost:9103'

        client = Client()
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)
        self.assertEqual(endpoints['datastore'], datastore_url)

    def test_env(self):
        base_url = 'http://www.stackstorm.com'
        api_url = 'http://www.st2.com:9101'
        datastore_url = 'http://www.st2.com:9103'

        os.environ['ST2_BASE_URL'] = base_url
        os.environ['ST2_API_URL'] = api_url
        os.environ['ST2_DATASTORE_URL'] = datastore_url
        self.assertEqual(os.environ.get('ST2_BASE_URL'), base_url)
        self.assertEqual(os.environ.get('ST2_API_URL'), api_url)
        self.assertEqual(os.environ.get('ST2_DATASTORE_URL'), datastore_url)

        client = Client()
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)
        self.assertEqual(endpoints['datastore'], datastore_url)

    def test_env_base_only(self):
        base_url = 'http://www.stackstorm.com'
        api_url = 'http://www.stackstorm.com:9101'
        datastore_url = 'http://www.stackstorm.com:9103'

        os.environ['ST2_BASE_URL'] = base_url
        self.assertEqual(os.environ.get('ST2_BASE_URL'), base_url)
        self.assertEqual(os.environ.get('ST2_API_URL'), None)
        self.assertEqual(os.environ.get('ST2_REACTOR_URL'), None)
        self.assertEqual(os.environ.get('ST2_DATASTORE_URL'), None)

        client = Client()
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)
        self.assertEqual(endpoints['datastore'], datastore_url)

    def test_args(self):
        base_url = 'http://www.stackstorm.com'
        api_url = 'http://www.st2.com:9101'
        datastore_url = 'http://www.st2.com:9103'

        client = Client(base_url=base_url, api_url=api_url, datastore_url=datastore_url)
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)
        self.assertEqual(endpoints['datastore'], datastore_url)

    def test_args_base_only(self):
        base_url = 'http://www.stackstorm.com'
        api_url = 'http://www.stackstorm.com:9101'
        datastore_url = 'http://www.stackstorm.com:9103'

        client = Client(base_url=base_url)
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)
        self.assertEqual(endpoints['datastore'], datastore_url)
