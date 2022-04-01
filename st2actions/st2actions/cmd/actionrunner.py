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

# Monkey patching should be done as early as possible.
# See http://eventlet.net/doc/patching.html#monkeypatching-the-standard-library
from __future__ import absolute_import

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import os
import signal
import sys

from st2actions import config
from st2actions import worker
from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.service_setup import deregister_service

__all__ = ["main"]

LOG = logging.getLogger(__name__)
ACTIONRUNNER = "actionrunner"


def _setup_sigterm_handler(action_worker):
    def sigterm_handler(signum=None, frame=None):
        # This will cause SystemExit to be throw and allow for component cleanup.
        action_worker.kill()

    # Register a SIGTERM signal handler which calls sys.exit which causes SystemExit to
    # be thrown. We catch SystemExit and handle cleanup there.
    signal.signal(signal.SIGTERM, sigterm_handler)


def _setup():
    capabilities = {"name": "actionrunner", "type": "passive"}
    common_setup(
        service=ACTIONRUNNER,
        config=config,
        setup_db=True,
        register_mq_exchanges=True,
        register_signal_handlers=True,
        service_registry=True,
        capabilities=capabilities,
    )


def _run_worker():
    LOG.info("(PID=%s) Worker started.", os.getpid())

    action_worker = worker.get_worker()
    _setup_sigterm_handler(action_worker)
    try:
        action_worker.start()
        action_worker.wait()
    except (KeyboardInterrupt, SystemExit):
        LOG.info("(PID=%s) Worker stopped.", os.getpid())

        errors = False

        try:
            deregister_service(service=ACTIONRUNNER)
            action_worker.shutdown()
        except:
            LOG.exception("Unable to shutdown worker.")
            errors = True

        if errors:
            return 1
    except:
        LOG.exception("(PID=%s) Worker unexpectedly stopped.", os.getpid())
        return 1

    return 0


def _teardown():
    common_teardown()


def main():
    try:
        _setup()
        return _run_worker()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except:
        LOG.exception("(PID=%s) Worker quit due to exception.", os.getpid())
        return 1
    finally:
        _teardown()
