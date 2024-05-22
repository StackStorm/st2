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
Stream WSGI application.

This application listens for events on the RabbitMQ message bus and delivers them to all the
clients which are connected to the stream HTTP endpoint (fan out approach).

Note: This app doesn't need access to MongoDB, just RabbitMQ.
"""

from oslo_config import cfg

from st2common.openapi import app
from st2stream import config as st2stream_config


def setup_app(config={}):
    common_setup = {
        "register_mq_exchanges": True,
        "register_internal_trigger_types": False,
        "run_migrations": False,
    }

    transforms = {"^/stream/v1/": ["/", "/v1/"]}

    return app.setup_app(
        service_name="stream",
        app_config=st2stream_config,
        oslo_cfg=cfg.CONF.stream,
        transforms=transforms,
        common_setup_kwargs=common_setup,
        config=config,
    )
