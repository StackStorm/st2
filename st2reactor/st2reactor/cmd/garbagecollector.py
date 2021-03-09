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

from oslo_config import cfg

from st2common import log as logging
from st2common.logging.misc import get_logger_name_for_module
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.constants.exit_codes import FAILURE_EXIT_CODE
from st2reactor.garbage_collector import config
from st2reactor.garbage_collector.base import GarbageCollectorService

__all__ = ["main"]


LOGGER_NAME = get_logger_name_for_module(sys.modules[__name__])
LOG = logging.getLogger(LOGGER_NAME)


def _setup():
    capabilities = {"name": "garbagecollector", "type": "passive"}
    common_setup(
        service="garbagecollector",
        config=config,
        setup_db=True,
        register_mq_exchanges=True,
        register_signal_handlers=True,
        register_runners=False,
        service_registry=True,
        capabilities=capabilities,
    )


def _teardown():
    common_teardown()


def main():
    try:
        _setup()

        collection_interval = cfg.CONF.garbagecollector.collection_interval
        sleep_delay = cfg.CONF.garbagecollector.sleep_delay
        garbage_collector = GarbageCollectorService(
            collection_interval=collection_interval, sleep_delay=sleep_delay
        )
        exit_code = garbage_collector.run()
    except SystemExit as exit_code:
        return exit_code
    except:
        LOG.exception("(PID:%s) GarbageCollector quit due to exception.", os.getpid())
        return FAILURE_EXIT_CODE
    finally:
        _teardown()

    return exit_code
