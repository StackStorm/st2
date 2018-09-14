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

from __future__ import absolute_import
import os
import sys

from st2common import log as logging
from st2common.logging.misc import get_logger_name_for_module
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.util.monkey_patch import monkey_patch
from st2reactor.rules import config
from st2reactor.rules import worker

monkey_patch()


LOGGER_NAME = get_logger_name_for_module(sys.modules[__name__])
LOG = logging.getLogger(LOGGER_NAME)


def _setup():
    common_setup(service='rulesengine', config=config, setup_db=True, register_mq_exchanges=True,
                 register_signal_handlers=True, register_internal_trigger_types=True)


def _teardown():
    common_teardown()


def _run_worker():
    LOG.info('(PID=%s) RulesEngine started.', os.getpid())

    rules_engine_worker = worker.get_worker()

    try:
        rules_engine_worker.start()
        return rules_engine_worker.wait()
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) RulesEngine stopped.', os.getpid())
        rules_engine_worker.shutdown()
    except:
        LOG.exception('(PID:%s) RulesEngine quit due to exception.', os.getpid())
        return 1

    return 0


def main():
    try:
        _setup()
        return _run_worker()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except:
        LOG.exception('(PID=%s) RulesEngine quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
