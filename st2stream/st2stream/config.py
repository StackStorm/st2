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
Configuration options registration and useful routines.
"""

from __future__ import absolute_import

import os

from oslo_config import cfg

import st2common.config as common_config
from st2common.openapi import config

CONF = cfg.CONF
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args(args=None):
    config.parse_args(args=args)


def register_opts(ignore_errors=False):
    config.register_opts(_register_app_opts, ignore_errors=ignore_errors)


def get_logging_config_path():
    return config.get_logging_config_path(cfg.CONF.stream)


def _register_app_opts(ignore_errors=False):
    # Note "allow_origin", "mask_secrets", "heartbeat" options are registered as part of st2common
    # config since they are also used outside st2stream
    stream_opts = config.get_base_opts("stream") + [
        cfg.StrOpt(
            "host", default="127.0.0.1", help="StackStorm stream API server host"
        ),
        cfg.IntOpt("port", default=9102, help="StackStorm API stream, server port"),
    ]

    common_config.do_register_opts(
        stream_opts, group="stream", ignore_errors=ignore_errors
    )
