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

from oslo_config import cfg

from st2common.openapi import app
from st2auth import config as st2auth_config
from st2auth.validation import validate_auth_backend_is_correctly_configured


def setup_app(config={}):
    common_setup = {
        "register_mq_exchanges": False,
        "register_internal_trigger_types": False,
        "run_migrations": False,
    }

    transforms = {"^/auth/v1/": ["/", "/v1/"]}

    pre_run_checks = [validate_auth_backend_is_correctly_configured]

    return app.setup_app(
        service_name="auth",
        app_config=st2auth_config,
        oslo_cfg=cfg.CONF.auth,
        pre_run_checks=pre_run_checks,
        transforms=transforms,
        common_setup_kwargs=common_setup,
        config=config,
    )
