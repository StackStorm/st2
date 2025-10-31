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

import sys

import six

from oslo_config import cfg
from tooz import coordination
from tooz import locking
from tooz.coordination import GroupNotCreated
from tooz.coordination import MemberNotJoined

from st2common import log as logging
from st2common.util import system_info


LOG = logging.getLogger(__name__)

COORDINATOR = None

__all__ = [
    "configured",
    "get_coordinator",
    "get_coordinator_if_set",
    "get_member_id",
    "coordinator_setup",
    "coordinator_teardown",
]


class NoOpLock(locking.Lock):
    def __init__(self, name="noop"):
        super(NoOpLock, self).__init__(name=name)

    def acquire(self, blocking=True):
        return True

    def release(self):
        return True

    def heartbeat(self):
        return True


class NoOpAsyncResult(object):
    """
    In most scenarios, tooz library returns an async result, a future and this
    class wrapper is here to correctly mimic tooz API and behavior.
    """

    def __init__(self, result=None):
        self._result = result

    def get(self):
        return self._result


class NoOpDriver(coordination.CoordinationDriver):
    """
    Tooz driver where each operation is a no-op.

    This driver is used if coordination service is not configured.
    """

    groups = {}

    def __init__(self, member_id, parsed_url=None, options=None):
        super(NoOpDriver, self).__init__(member_id, parsed_url, options)

    @classmethod
    def stop(cls):
        cls.groups = {}

    def watch_join_group(self, group_id, callback):
        self._hooks_join_group[group_id].append(callback)

    def unwatch_join_group(self, group_id, callback):
        return None

    def watch_leave_group(self, group_id, callback):
        return None

    def unwatch_leave_group(self, group_id, callback):
        return None

    def watch_elected_as_leader(self, group_id, callback):
        return None

    def unwatch_elected_as_leader(self, group_id, callback):
        return None

    @staticmethod
    def stand_down_group_leader(group_id):
        return None

    @classmethod
    def create_group(cls, group_id):
        cls.groups[group_id] = {"members": {}}
        return NoOpAsyncResult()

    @classmethod
    def get_groups(cls):
        return NoOpAsyncResult(result=cls.groups.keys())

    @classmethod
    def join_group(cls, group_id, capabilities=""):
        member_id = get_member_id()

        cls.groups[group_id]["members"][member_id] = {"capabilities": capabilities}
        return NoOpAsyncResult()

    @classmethod
    def leave_group(cls, group_id):
        member_id = get_member_id()
        try:
            members = cls.groups[group_id]["members"]
        except KeyError:
            raise GroupNotCreated(group_id)

        try:
            del members[member_id]
        except KeyError:
            raise MemberNotJoined(group_id, member_id)
        return NoOpAsyncResult()

    @classmethod
    def delete_group(cls, group_id):
        try:
            del cls.groups[group_id]
        except KeyError:
            raise GroupNotCreated(group_id)
        return NoOpAsyncResult()

    @classmethod
    def get_members(cls, group_id):
        try:
            member_ids = cls.groups[group_id]["members"].keys()
        except KeyError:
            raise GroupNotCreated("Group doesnt exist")

        return NoOpAsyncResult(result=member_ids)

    @classmethod
    def get_member_capabilities(cls, group_id, member_id):
        member_capabiliteis = cls.groups[group_id]["members"][member_id]["capabilities"]
        return NoOpAsyncResult(result=member_capabiliteis)

    @staticmethod
    def update_capabilities(group_id, capabilities):
        return None

    @staticmethod
    def get_leader(group_id):
        return None

    @staticmethod
    def get_lock(name):
        return NoOpLock(name="noop")


def configured():
    """
    Return True if the coordination service is properly configured.

    :rtype: ``bool``
    """
    backend_configured = cfg.CONF.coordination.url is not None
    mock_backend = backend_configured and (
        cfg.CONF.coordination.url.startswith("zake")
        or cfg.CONF.coordination.url.startswith("file")
    )

    return backend_configured and not mock_backend


def get_driver_name() -> str:
    """
    Return coordination driver name (aka protocol part from the URI / URL).
    """
    url = cfg.CONF.coordination.url

    if not url:
        return None

    driver_name = url.split("://")[0]
    return driver_name


def coordinator_setup(start_heart=True):
    """
    Sets up the client for the coordination service.

    URL examples for connection:
        zake://
        file:///tmp
        redis://username:password@host:port
        mysql://username:password@host:port/dbname
    """
    url = cfg.CONF.coordination.url
    lock_timeout = cfg.CONF.coordination.lock_timeout
    member_id = get_member_id()

    if url:
        coordinator = coordination.get_coordinator(
            url, member_id, lock_timeout=lock_timeout
        )
    else:
        # Use a no-op backend
        # Note: We don't use tooz to obtain a reference since for this to work we would need to
        # register a plugin inside setup.py entry_point and use python setup.py develop for tests
        # to work
        coordinator = NoOpDriver(member_id)

    coordinator.start(start_heart=start_heart)
    return coordinator


def coordinator_teardown(coordinator=None):
    if coordinator:
        coordinator.stop()


def get_coordinator(start_heart=True, use_cache=True):
    """
    :param start_heart: True to start heartbeating process.
    :type start_heart: ``bool``

    :param use_cache: True to use cached coordinator instance. False should only be used in tests.
    :type use_cache: ``bool``
    """
    global COORDINATOR

    if not configured():
        extra_msg = ""
        # sys._called_from_test set in conftest.py for pytest runs
        if "nose" in sys.modules.keys() or hasattr(sys, "_called_from_test"):
            extra_msg = (
                " Set ST2TESTS_REDIS_HOST and ST2TESTS_REDIS_PORT env vars to "
                "configure the coordination backend for unit and integration tests."
            )
        LOG.warning(
            "Coordination backend is not configured. Code paths which use coordination "
            "service will use best effort approach and race conditions are possible."
            f"{extra_msg}"
        )

    if not use_cache:
        return coordinator_setup(start_heart=start_heart)

    if not COORDINATOR:
        COORDINATOR = coordinator_setup(start_heart=start_heart)
        LOG.debug(
            "Initializing and caching new coordinator instance: %s" % (str(COORDINATOR))
        )
    else:
        LOG.debug("Using cached coordinator instance: %s" % (str(COORDINATOR)))

    return COORDINATOR


def get_coordinator_if_set():
    """
    Return a coordinator instance if one has been initialized, None otherwise.
    """
    global COORDINATOR
    return COORDINATOR


def get_member_id():
    """
    Retrieve member if for the current process.

    :rtype: ``bytes``
    """
    proc_info = system_info.get_process_info()
    member_id = six.b("%s_%d" % (proc_info["hostname"], proc_info["pid"]))
    return member_id


def get_group_id(service):
    if not isinstance(service, six.binary_type):
        group_id = service.encode("utf-8")
    else:
        group_id = service
    return group_id
