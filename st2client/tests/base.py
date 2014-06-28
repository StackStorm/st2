import json
import logging

from st2client import models


LOG = logging.getLogger(__name__)

FAKE_ENDPOINT = 'http://localhost:8268'

RESOURCES = [
    {
        "id": "123",
        "name": "abc",
    },
    {
        "id": "456",
        "name": "def"
    }
]


class FakeResource(models.Resource):
    _plural = 'FakeResources'


class FakeResponse(object):

    def __init__(self, text, status_code, reason):
        self.text = text
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        raise Exception(self.reason)


class FakeClient(object):

    def __init__(self):
        self.managers = {
            'FakeResource': models.ResourceManager(FakeResource,
                                                   FAKE_ENDPOINT)
        }


class FakeApp(object):

    def __init__(self):
        self.client = FakeClient()
