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

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import sys

import eventlet
from oslo_config import cfg

from st2common import log as logging
from st2stream import config
from st2common.openapi import api

config.register_opts(ignore_errors=True)

from st2stream import app

__all__ = ["main"]


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if "--use-debugger" in sys.argv else True,
    time=True,
)

LOG = logging.getLogger(__name__)


def main():
    common_setup = {
        "register_mq_exchanges": True,
        "register_internal_trigger_types": False,
        "run_migrations": False,
    }

    api.run(
        service_name="stream",
        app_config=config,
        cfg=cfg.CONF.stream,
        app=app,
        log=LOG,
        use_custom_pool=True,
        log_output=True,
        common_setup_kwargs=common_setup,
    )
