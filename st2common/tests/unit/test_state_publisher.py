# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import kombu
import mock
import mongoengine as me

from st2common.models import db
from st2common.models.db import stormbase
from st2common.persistence import base as persistence
from st2common.transport import publishers

from st2tests import DbTestCase


# PoolPublisher is mocked, so this does not need messaging.prefix
FAKE_STATE_MGMT_XCHG = kombu.Exchange("st2.fake.state", type="topic")


class FakeModelPublisher(publishers.StatePublisherMixin):
    def __init__(self):
        super(FakeModelPublisher, self).__init__(exchange=FAKE_STATE_MGMT_XCHG)


class FakeModelDB(stormbase.StormBaseDB):
    state = me.StringField(required=True)


class FakeModel(persistence.Access):
    impl = db.MongoDBAccess(FakeModelDB)
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_publisher(cls):
        if not cls.publisher:
            cls.publisher = FakeModelPublisher()
        return cls.publisher

    @classmethod
    def publish_state(cls, model_object):
        publisher = cls._get_publisher()
        if publisher:
            publisher.publish_state(model_object, getattr(model_object, "state", None))

    @classmethod
    def _get_by_object(cls, object):
        return None


class StatePublisherTest(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super(StatePublisherTest, cls).setUpClass()
        cls.access = FakeModel()

    def tearDown(self):
        FakeModelDB.drop_collection()
        super(StatePublisherTest, self).tearDown()

    @mock.patch.object(publishers.PoolPublisher, "publish", mock.MagicMock())
    def test_publish(self):
        instance = FakeModelDB(state="faked")
        self.access.publish_state(instance)
        publishers.PoolPublisher.publish.assert_called_with(
            instance, FAKE_STATE_MGMT_XCHG, instance.state
        )

    def test_publish_unset(self):
        instance = FakeModelDB()
        self.assertRaises(Exception, self.access.publish_state, instance)

    def test_publish_none(self):
        instance = FakeModelDB(state=None)
        self.assertRaises(Exception, self.access.publish_state, instance)

    def test_publish_empty_str(self):
        instance = FakeModelDB(state="")
        self.assertRaises(Exception, self.access.publish_state, instance)
