# -*- coding: utf-8 -*-
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

"""
This file is used to test edge case with logging unicode data.
"""

from __future__ import absolute_import

# Ignore CryptographyDeprecationWarning warnings which appear on Python 3.6
# TODO: Remove after dropping python3.6
import warnings

warnings.filterwarnings("ignore", message="Python 3.6 is no longer supported")

import os
import sys

from oslo_config import cfg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ST2ACTIONS_PATH = os.path.join(BASE_DIR, "../../../st2actions")
ST2COMMON_PATH = os.path.join(BASE_DIR, "../../")
ST2TESTS_PATH = os.path.join(BASE_DIR, "../../../st2tests")

# Ensure st2actions is in PYTHONPATH.
# This is needed since this script is spawned from inside integration tests
sys.path.append(ST2ACTIONS_PATH)
sys.path.append(ST2COMMON_PATH)
sys.path.append(ST2TESTS_PATH)

from st2actions.notifier import config
from st2common import log as logging
from st2common.service_setup import setup as common_setup

# Do not use helpers from st2tests to calculate this (avoid extra imports).
FIXTURES_DIR = os.path.join(ST2TESTS_PATH, "st2tests/fixtures")
ST2_CONFIG_DEBUG_LL_PATH = os.path.join(
    FIXTURES_DIR, "conf/st2.tests.api.debug_log_level.conf"
)

LOG = logging.getLogger(__name__)


def main():
    cfg.CONF.set_override("debug", True)
    common_setup(
        service="test",
        config=config,
        setup_db=False,
        run_migrations=False,
        register_runners=False,
        register_internal_trigger_types=False,
        register_mq_exchanges=False,
        register_signal_handlers=False,
        service_registry=False,
        config_args=["--config-file", ST2_CONFIG_DEBUG_LL_PATH],
    )

    LOG.info("Test info message 1")
    LOG.debug("Test debug message 1")

    # 1. Actual unicode sequence
    LOG.info("Test info message with unicode 1 - 好好好")
    LOG.debug("Test debug message with unicode 1 - 好好好")

    # 2. Ascii escape sequence
    LOG.info(
        "Test info message with unicode 1 - "
        + "好好好".encode("ascii", "backslashreplace").decode("ascii", "backslashreplace")
    )
    LOG.debug(
        "Test debug message with unicode 1 - "
        + "好好好".encode("ascii", "backslashreplace").decode("ascii", "backslashreplace")
    )


if __name__ == "__main__":
    main()
