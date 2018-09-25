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

from st2common.constants.exit_codes import FAILURE_EXIT_CODE
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown

__all__ = [
    'ActiveService',
    'PassiveService',

    'run_service'
]


class BaseService(object):
    name = None
    config = None

    setup_db = True
    register_mq_exchanges = True
    register_signal_handlers = True
    register_internal_trigger_types = False
    run_migrations = True

    def __init__(self, logger):
        self.logger = logger

        self.pid = os.getpid()
        self._started = False

    def setup(self):
        common_setup(service=self.name, config=self.config, setup_db=self.setup_db,
                     register_mq_exchanges=self.register_mq_exchanges,
                     register_signal_handlers=self.register_signal_handlers,
                     register_internal_trigger_types=self.register_internal_trigger_types,
                     run_migrations=self.run_migrations)

    def start(self):
        self._started = True

    def stop(self):
        self._started = False
        common_teardown()


class ActiveService(BaseService):
    """
    Service which listens on TCP / HTTP interface.
    """
    def __init__(self, logger, host, port):
        super(ActiveService, self).__init__(logger=logger)

        self._host = host
        self._port = port

        self._socket = None  # reference to the bound socket
        self._server = None  # reference to the WSGI HTTP server


class PassiveService(BaseService):
    """
    Service which doesn't listen on any port and just consumes messages of the messages bus.
    """
    pass


def run_service(service):
    """
    Utility function for running a service.

    This function takes care of starting the service and stop it on exception.

    :return: Service exit code.
    """

    try:
        service.setup()
        return service.start()
    except (KeyboardInterrupt, SystemExit):
        service.logger.info('(PID=%s) StackStorm %s stopped.', os.getpid(), service.name)
        return FAILURE_EXIT_CODE
    except Exception:
        service.logger.exception('(PID=%s) StackStorm %s quit due to exception.', service.pid,
                                 service.name)
        return FAILURE_EXIT_CODE
    finally:
        service.stop()
