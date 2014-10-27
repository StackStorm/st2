import os
import json
import mock
import tempfile
import requests
import logging

from tests import base
from st2client import shell


LOG = logging.getLogger(__name__)

USERNAME = 'stanley'
PASSWORD = 'ShhhDontTell'
HEADERS = {'content-type': 'application/json'}
AUTH_URL = 'https://localhost:9100/tokens'
GET_RULES_URL = 'http://localhost:9101/rules'


class TestHttps(base.BaseCLITestCase):

    def __init__(self, *args, **kwargs):
        super(TestHttps, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()

    def setUp(self):
        super(TestHttps, self).setUp()

        # Setup environment.
        os.environ['ST2_BASE_URL'] = 'http://localhost'
        if 'ST2_CACERT' in os.environ:
            del os.environ['ST2_CACERT']

        # Create a temp file to mock a cert file.
        self.cacert_fd, self.cacert_path = tempfile.mkstemp()

    def tearDown(self):
        super(TestHttps, self).tearDown()

        # Clean up environment.
        if 'ST2_CACERT' in os.environ:
            del os.environ['ST2_CACERT']
        if 'ST2_BASE_URL' in os.environ:
            del os.environ['ST2_BASE_URL']

        # Clean up temp files.
        os.close(self.cacert_fd)
        os.unlink(self.cacert_path)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_https_without_cacert(self):
        self.shell.run(['auth', USERNAME, '-p', PASSWORD])
        kwargs = {'verify': False, 'headers': HEADERS, 'auth': (USERNAME, PASSWORD)}
        requests.post.assert_called_with(AUTH_URL, json.dumps({}), **kwargs)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_https_with_cacert_from_cli(self):
        self.shell.run(['--cacert', self.cacert_path, 'auth', USERNAME, '-p', PASSWORD])
        kwargs = {'verify': self.cacert_path, 'headers': HEADERS, 'auth': (USERNAME, PASSWORD)}
        requests.post.assert_called_with(AUTH_URL, json.dumps({}), **kwargs)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_https_with_cacert_from_env(self):
        os.environ['ST2_CACERT'] = self.cacert_path
        self.shell.run(['auth', USERNAME, '-p', PASSWORD])
        kwargs = {'verify': self.cacert_path, 'headers': HEADERS, 'auth': (USERNAME, PASSWORD)}
        requests.post.assert_called_with(AUTH_URL, json.dumps({}), **kwargs)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps([]), 200, 'OK')))
    def test_decorate_http_without_cacert(self):
        self.shell.run(['rule', 'list'])
        kwargs = {'params': {}}
        requests.get.assert_called_with(GET_RULES_URL, **kwargs)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_http_with_cacert_from_cli(self):
        self.shell.run(['--cacert', self.cacert_path, 'rule', 'list'])
        kwargs = {'params': {}}
        requests.get.assert_called_with(GET_RULES_URL, **kwargs)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_http_with_cacert_from_env(self):
        os.environ['ST2_CACERT'] = self.cacert_path
        self.shell.run(['rule', 'list'])
        kwargs = {'params': {}}
        requests.get.assert_called_with(GET_RULES_URL, **kwargs)
