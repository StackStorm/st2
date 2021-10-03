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

from st2actions.scheduler import config
from st2common import log as logging
from st2common.service_setup import teardown as common_teardown
from st2common.service_setup import setup as common_setup

__all__ = ["main"]

LOG = logging.getLogger(__name__)


def _setup_sigterm_handler():
    def sigterm_handler(signum=None, frame=None):
        # This will cause SystemExit to be throw and allow for component cleanup.
        sys.exit(0)

    # Register a SIGTERM signal handler which calls sys.exit which causes SystemExit to
    # be thrown. We catch SystemExit and handle cleanup there.
    signal.signal(signal.SIGTERM, sigterm_handler)


def _setup():
    capabilities = {"name": "scheduler", "type": "passive"}
    common_setup(
        service="scheduler",
        config=config,
        setup_db=True,
        register_mq_exchanges=True,
        register_signal_handlers=True,
        service_registry=True,
        capabilities=capabilities,
    )

    _setup_sigterm_handler()


def _run_scheduler():
    LOG.info("(PID=%s) Scheduler started.", os.getpid())

    # Lazy load these so that decorator metrics are in place.
    from st2actions.scheduler import (
        handler as scheduler_handler,
        entrypoint as scheduler_entrypoint,
    )

    handler = scheduler_handler.get_handler()
    entrypoint = scheduler_entrypoint.get_scheduler_entrypoint()

    # TODO: Remove this try block for _cleanup_policy_delayed in v3.2.
    # This is a temporary cleanup to remove executions in deprecated policy-delayed status.
    try:
        handler._cleanup_policy_delayed()
    except Exception:
        LOG.exception(
            "(PID=%s) Scheduler unable to perform migration cleanup.", os.getpid()
        )

    # TODO: Remove this try block for _fix_missing_action_execution_id in v3.2.
    # This is a temporary fix to auto-populate action_execution_id.
    try:
        handler._fix_missing_action_execution_id()
    except Exception:
        LOG.exception(
            "(PID=%s) Scheduler unable to populate action_execution_id.", os.getpid()
        )

    try:
        handler.start()
        entrypoint.start()

        # Wait on handler first since entrypoint is more durable.
        handler.wait() or entrypoint.wait()
    except (KeyboardInterrupt, SystemExit):
        LOG.info("(PID=%s) Scheduler stopped.", os.getpid())

        errors = False

        try:
            handler.shutdown()
            entrypoint.shutdown()
        except:
            LOG.debug("Unable to shutdown scheduler.", exc_info=True)
            errors = True

        if errors:
            return 1
    except:
        LOG.exception("(PID=%s) Scheduler unexpectedly stopped.", os.getpid())

        try:
            handler.shutdown()
            entrypoint.shutdown()
        except:
            LOG.exception("Unable to shutdown scheduler.")

        return 1

    return 0


def _teardown():
    common_teardown()


def main():
    try:
        _setup()
        return _run_scheduler()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except:
        LOG.exception("(PID=%s) Scheduler quit due to exception.", os.getpid())
        return 1
    finally:
        _teardown()
