# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg
from tooz import coordination
from tooz import locking

from st2common import log as logging
from st2common.util import system_info


LOG = logging.getLogger(__name__)

COORDINATOR = None

__all__ = [
    'configured',
    'get_coordinator',

    'coordinator_setup',
    'coordinator_teardown'
]


class NoOpLock(locking.Lock):
    def __init__(self, name='noop'):
        super(NoOpLock, self).__init__(name=name)

    def acquire(self, blocking=True):
        pass

    def release(self):
        pass

    def heartbeat(self):
        pass


class NoOpDriver(coordination.CoordinationDriver):
    """
    Tooz driver where each operation is a no-op.

    This driver is used if coordination service is not configured.
    """

    def __init__(self):
        super(NoOpDriver, self).__init__()

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

    @staticmethod
    def create_group(group_id):
        return None

    @staticmethod
    def get_groups():
        return None

    @staticmethod
    def join_group(group_id, capabilities=''):
        return None

    @staticmethod
    def leave_group(group_id):
        return None

    @staticmethod
    def delete_group(group_id):
        return None

    @staticmethod
    def get_members(group_id):
        return None

    @staticmethod
    def get_member_capabilities(group_id, member_id):
        return None

    @staticmethod
    def update_capabilities(group_id, capabilities):
        return None

    @staticmethod
    def get_leader(group_id):
        return None

    @staticmethod
    def get_lock(name):
        return NoOpLock(name='noop')


def configured():
    """
    Return True if the coordination service is properly configured.

    :rtype: ``bool``
    """
    backend_configured = cfg.CONF.coordination.url is not None
    mock_backend = backend_configured and (cfg.CONF.coordination.url.startswith('zake') or
                                           cfg.CONF.coordination.url.startswith('file'))

    return backend_configured and not mock_backend


def coordinator_setup():
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
    proc_info = system_info.get_process_info()
    member_id = '%s_%d' % (proc_info['hostname'], proc_info['pid'])

    if url:
        coordinator = coordination.get_coordinator(url, member_id, lock_timeout=lock_timeout)
    else:
        # Use a no-op backend
        # Note: We don't use tooz to obtain a reference since for this to work we would need to
        # register a plugin inside setup.py entry_point and use python setup.py develop for tests
        # to work
        coordinator = NoOpDriver()

    coordinator.start()
    return coordinator


def coordinator_teardown(coordinator):
    coordinator.stop()


def get_coordinator():
    global COORDINATOR

    if not configured():
        LOG.warn('Coordination backend is not configured. Code paths which use coordination '
                 'service will use best effort approach and race conditions are possible.')

    if not COORDINATOR:
        COORDINATOR = coordinator_setup()

    return COORDINATOR
