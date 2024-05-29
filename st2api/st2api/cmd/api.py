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

# NOTE: It's important that we perform monkey patch as early as possible before any other modules
# are important, otherwise SSL support for MongoDB won't work.
# See https://github.com/StackStorm/st2/issues/4832 and https://github.com/gevent/gevent/issues/1016
# for details.
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

from oslo_config import cfg

from st2common import log as logging
from st2api import config
from st2common.openapi import api

config.register_opts(ignore_errors=True)

from st2api import app
from st2api.validation import validate_auth_cookie_is_correctly_configured
from st2api.validation import validate_rbac_is_correctly_configured

__all__ = ["main"]

LOG = logging.getLogger(__name__)


def main():
    common_setup = {
        "register_mq_exchanges": True,
        "register_internal_trigger_types": True,
    }

    pre_run_checks = [
        validate_auth_cookie_is_correctly_configured,
        validate_rbac_is_correctly_configured,
    ]

    api.run(
        service_name="api",
        app_config=config,
        cfg=cfg.CONF.api,
        app=app,
        log=LOG,
        use_custom_pool=False,
        log_output=False,
        common_setup_kwargs=common_setup,
        pre_run_checks=pre_run_checks,
    )
