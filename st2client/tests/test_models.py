import mock
import json
import logging
import unittest

from st2client import models
from st2client.utils import httpclient


LOG = logging.getLogger(__name__)


RESOURCES = [
    {
        "id": "abc123",
        "name": "one",
    },
    {
        "id": "def456",
        "name": "two"
    }
]


class FakeResource(models.Resource):
    _plural = 'Resources'


class FakeResponse(object):

    def __init__(self, text, status_code, reason):
        self.text = text
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        raise Exception(self.reason)


class TestResourceManager(unittest.TestCase):

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=\
            FakeResponse(json.dumps(RESOURCES), 200, 'OK')))
    def test_get_all(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        resources = mgr.get_all()
        actual = [resource.serialize() for resource in resources]
        expected = json.loads(json.dumps(RESOURCES))
        self.assertListEqual(actual, expected)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=\
            FakeResponse('', 500, 'INTERNAL SERVER ERROR')))
    def test_get_all_failed(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        self.assertRaises(Exception, mgr.get_all)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=\
            FakeResponse(json.dumps(RESOURCES[0]), 200, 'OK')))
    def test_get_by_id(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        resource = mgr.get_by_id('abc123')
        actual = resource.serialize()
        expected = json.loads(json.dumps(RESOURCES[0]))
        self.assertEqual(actual, expected)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=\
            FakeResponse('', 500, 'INTERNAL SERVER ERROR')))
    def test_get_by_id_failed(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        self.assertRaises(Exception, mgr.get_by_id)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=\
            FakeResponse(json.dumps([RESOURCES[0]]), 200, 'OK')))
    def test_get_by_name(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        resource = mgr.get_by_name('one')
        actual = resource.serialize()
        expected = json.loads(json.dumps(RESOURCES[0]))
        self.assertEqual(actual, expected)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=\
            FakeResponse(json.dumps(RESOURCES), 200, 'OK')))
    def test_get_by_name_ambiguous(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        resource = mgr.get_by_name('one')
        self.assertIsNone(resource)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=\
            FakeResponse('', 500, 'INTERNAL SERVER ERROR')))
    def test_get_by_name_failed(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        self.assertRaises(Exception, mgr.get_by_name)

    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=\
            FakeResponse(json.dumps(RESOURCES[0]), 200, 'OK')))
    def test_create(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        instance = FakeResource.deserialize('{"name": "one"}')
        resource = mgr.create(instance)
        self.assertIsNotNone(resource)

    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=\
            FakeResponse('', 500, 'INTERNAL SERVER ERROR')))
    def test_create_failed(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        instance = FakeResource.deserialize('{"name": "one"}')
        self.assertRaises(Exception, mgr.create, instance)

    @mock.patch.object(
        httpclient.HTTPClient, 'put',
        mock.MagicMock(return_value=\
            FakeResponse(json.dumps(RESOURCES[0]), 200, 'OK')))
    def test_update(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        instance = FakeResource.deserialize('{"id": "abc123", "name": "uno"}')
        resource = mgr.update(instance)
        self.assertIsNotNone(resource)

    @mock.patch.object(
        httpclient.HTTPClient, 'put',
        mock.MagicMock(return_value=\
            FakeResponse('', 500, 'INTERNAL SERVER ERROR')))
    def test_update_failed(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        instance = FakeResource.deserialize('{"id": "abc123", "name": "uno"}')
        self.assertRaises(Exception, mgr.update, instance)

    @mock.patch.object(
        httpclient.HTTPClient, 'delete',
        mock.MagicMock(return_value=\
            FakeResponse('', 204, 'NO CONTENT')))
    def test_delete(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        mgr.delete('abc123')

    @mock.patch.object(
        httpclient.HTTPClient, 'delete',
        mock.MagicMock(return_value=\
            FakeResponse('', 500, 'INTERNAL SERVER ERROR')))
    def test_delete_failed(self):
        mgr = models.ResourceManager(FakeResource, 'http://localhost:9999')
        self.assertRaises(Exception, mgr.delete, 'abc123')
