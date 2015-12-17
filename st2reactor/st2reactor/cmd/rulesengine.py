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

import os
import sys

import eventlet
from oslo_config import cfg

from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2reactor.rules import config
from st2reactor.rules import worker
from st2reactor.timer.base import St2Timer

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

LOG = logging.getLogger('st2reactor.bin.rulesengine')


def _setup():
    common_setup(service='rulesengine', config=config, setup_db=True, register_mq_exchanges=True,
                 register_signal_handlers=True)


def _teardown():
    common_teardown()


def _kickoff_timer(timer):
    timer.start()


def _run_worker():
    LOG.info('(PID=%s) RulesEngine started.', os.getpid())

    timer = St2Timer(local_timezone=cfg.CONF.timer.local_timezone)
    rules_engine_worker = worker.get_worker()

    try:
        timer_thread = eventlet.spawn(_kickoff_timer, timer)
        rules_engine_worker.start()
        return timer_thread.wait() and rules_engine_worker.wait()
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) RulesEngine stopped.', os.getpid())
        rules_engine_worker.shutdown()
    except:
        LOG.exception('(PID:%s) RulesEngine quit due to exception.', os.getpid())
        return 1
    finally:
        timer.cleanup()

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
