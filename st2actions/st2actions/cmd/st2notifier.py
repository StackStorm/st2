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
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2actions.notifier import config
from st2actions.notifier import notifier

__all__ = ["main"]

LOG = logging.getLogger(__name__)


def _setup():
    capabilities = {"name": "notifier", "type": "passive"}
    common_setup(
        service="notifier",
        config=config,
        setup_db=True,
        register_mq_exchanges=True,
        register_signal_handlers=True,
        service_registry=True,
        capabilities=capabilities,
    )


def _run_worker():
    LOG.info("(PID=%s) Actions notifier started.", os.getpid())
    actions_notifier = notifier.get_notifier()
    try:
        actions_notifier.start(wait=True)
    except (KeyboardInterrupt, SystemExit):
        LOG.info("(PID=%s) Actions notifier stopped.", os.getpid())
        actions_notifier.shutdown()
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
        LOG.exception("(PID=%s) Results tracker quit due to exception.", os.getpid())
        return 1
    finally:
        _teardown()
