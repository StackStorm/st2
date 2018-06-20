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

# Monkey patching should be done as early as possible.
# See http://eventlet.net/doc/patching.html#monkeypatching-the-standard-library

from __future__ import absolute_import

from st2common.util.monkey_patch import monkey_patch
monkey_patch()

import os
import signal
import sys
import traceback

from st2actions.workflows import config
from st2actions.workflows import workflows
from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown

__all__ = [
    'main'
]

LOG = logging.getLogger(__name__)


def setup_sigterm_handler():

        def sigterm_handler(signum=None, frame=None):
            # This will cause SystemExit to be throw and allow for component cleanup.
            sys.exit(0)

        # Register a SIGTERM signal handler which calls sys.exit which causes SystemExit to
        # be thrown. We catch SystemExit and handle cleanup there.
        signal.signal(signal.SIGTERM, sigterm_handler)


def setup():
    common_setup(
        service='workflow_engine',
        config=config,
        setup_db=True,
        register_mq_exchanges=True,
        register_signal_handlers=True
    )

    setup_sigterm_handler()


def run_server():
    LOG.info('(PID=%s) Workflow engine started.', os.getpid())

    engine = workflows.get_engine()

    try:
        engine.start(wait=True)
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) Workflow engine stopped.', os.getpid())
        engine.shutdown()
    except:
        LOG.exception('(PID=%s) Workflow engine unexpectedly stopped.', os.getpid())
        return 1

    return 0


def teardown():
    common_teardown()


def main():
    try:
        setup()
        return run_server()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except Exception:
        traceback.print_exc()
        LOG.exception('(PID=%s) Workflow engine quit due to exception.', os.getpid())
        return 1
    finally:
        teardown()
