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

import sys

import eventlet
from oslo_config import cfg

from st2common import log as logging
from st2common.constants.timer import TIMER_ENABLED_LOG_LINE, TIMER_DISABLED_LOG_LINE
from st2common.logging.misc import get_logger_name_for_module
from st2common.service import PassiveService
from st2common.service import run_service
from st2common.util.monkey_patch import monkey_patch
from st2reactor.timer import config
from st2reactor.timer.base import St2Timer

monkey_patch()

LOGGER_NAME = get_logger_name_for_module(sys.modules[__name__])
LOG = logging.getLogger(LOGGER_NAME)


class TimersEngineService(PassiveService):
    name = 'timersengine'
    config = config

    setup_db = True
    register_mq_exchanges = True
    register_signal_handlers = True
    register_internal_trigger_types = True
    run_migrations = True

    def __init__(self, logger):
        super(TimersEngineService, self).__init__(logger=logger)

        self._timer = None
        self._timer_thread = None

    def start(self):
        LOG.info('(PID=%s) TimerEngine started.', self.pid)

        enabled = cfg.CONF.timer.enable or cfg.CONF.timersengine.enable

        if not enabled:
            self.logger.info(TIMER_DISABLED_LOG_LINE)
            return

        def start_timer(timer):
            timer.start()

        local_tz = cfg.CONF.timer.local_timezone or cfg.CONF.timersengine.local_timezone
        self._timer = St2Timer(local_timezone=local_tz)
        self._timer_thread = eventlet.spawn(start_timer, self._timer)

        self.logger.info(TIMER_ENABLED_LOG_LINE)
        self._timer_thread.wait()

    def stop(self):
        super(TimersEngineService, self).stop()

        if self._timer:
            self._timer.cleanup()


def main():
    service = TimersEngineService(logger=LOG)
    exit_code = run_service(service=service)
    return exit_code
