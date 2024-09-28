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

from oslo_config import cfg

from st2common import log as logging
from st2auth import config
from st2common.openapi import api

config.register_opts(ignore_errors=True)

from st2auth import app
from st2auth.validation import validate_auth_backend_is_correctly_configured


__all__ = ["main"]


LOG = logging.getLogger(__name__)


def main():
    common_setup = {
        "register_mq_exchanges": False,
        "register_internal_trigger_types": False,
        "run_migrations": False,
    }

    pre_run_checks = [validate_auth_backend_is_correctly_configured]

    api.run(
        service_name="auth",
        app_config=config,
        cfg=cfg.CONF.auth,
        app=app,
        log=LOG,
        use_custom_pool=True,
        log_output=True,
        common_setup_kwargs=common_setup,
        pre_run_checks=pre_run_checks,
    )
