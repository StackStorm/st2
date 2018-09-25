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
from st2common.service import PassiveService
from st2common.service import run_service
from st2common.util.monkey_patch import monkey_patch
from st2reactor.rules import config
from st2reactor.rules import worker

monkey_patch()


LOGGER_NAME = get_logger_name_for_module(sys.modules[__name__])
LOG = logging.getLogger(LOGGER_NAME)


class RulesEngineService(PassiveService):
    name = 'rulesengine'
    config = config

    setup_db = True
    register_mq_exchanges = True
    register_signal_handlers = True
    register_internal_trigger_types = True
    run_migrations = True

    def __init__(self, logger):
        super(RulesEngineService, self).__init__(logger=logger)

        self._worker = None

    def start(self):
        self.logger.info('(PID=%s) RulesEngine started.', os.getpid())

        self._worker = worker.get_worker()

        self._worker.start()
        self._worker.wait()

    def stop(self):
        if self._worker:
            self._worker.shutdown()


def main():
    service = RulesEngineService(logger=LOG)
    exit_code = run_service(service=service)
    return exit_code
