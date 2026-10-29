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

import os
import sys

from st2common import log as logging
from st2common.logging.misc import get_logger_name_for_module
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.service_setup import deregister_service
from st2common.util import concurrency
from st2reactor.rules import config
from st2reactor.rules import worker

LOGGER_NAME = get_logger_name_for_module(sys.modules[__name__])
LOG = logging.getLogger(LOGGER_NAME)
RULESENGINE = "rulesengine"


def _setup():
    capabilities = {"name": "rulesengine", "type": "passive"}
    common_setup(
        service=RULESENGINE,
        config=config,
        setup_db=True,
        register_mq_exchanges=True,
        register_signal_handlers=True,
        register_internal_trigger_types=True,
        register_runners=False,
        service_registry=True,
        capabilities=capabilities,
    )


def _teardown():
    common_teardown()


def _run_worker():
    LOG.info("(PID=%s) RulesEngine started.", os.getpid())

    rules_engine_worker = worker.get_worker()

    try:
        rules_engine_worker.start()

        # Monitor the worker thread - if it dies/fails, we need to exit cleanly
        # Poll the worker thread to detect failures
        while True:
            if (
                rules_engine_worker._consumer_thread
                and rules_engine_worker._consumer_thread.dead
            ):
                # Thread died - try to get the exception if it raised one
                try:
                    concurrency.wait(
                        rules_engine_worker._consumer_thread
                    )  # This will raise if thread raised
                except Exception as e:
                    LOG.error("RulesEngine worker thread failed: %s", e)
                    raise
                # Thread completed successfully (shouldn't happen in normal operation)
                LOG.info("RulesEngine worker thread completed")
                return 0

            # Sleep briefly to avoid tight loop
            concurrency.sleep(0.1)
    except (KeyboardInterrupt, SystemExit):
        LOG.info("(PID=%s) RulesEngine stopped.", os.getpid())
        deregister_service(RULESENGINE)
        rules_engine_worker.shutdown()
        raise
    except:
        LOG.exception("(PID=%s) RulesEngine quit due to exception.", os.getpid())
        rules_engine_worker.shutdown()
        raise

    return 0


def main():
    try:
        _setup()
        return _run_worker()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except:
        LOG.exception("(PID=%s) RulesEngine quit due to exception.", os.getpid())
        raise
    finally:
        _teardown()
