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

from oslo.config import cfg

import st2common.config as common_config
common_config.register_opts()

CONF = cfg.CONF


def _register_common_opts():
    common_config.register_opts()


def _register_reactor_opts():
    logging_opts = [
        cfg.StrOpt('logging', default='etc/logging.conf',
                   help='location of the logging.conf file')
    ]
    CONF.register_opts(logging_opts, group='reactor')

    sensor_test_opt = cfg.StrOpt('sensor-path', help='Path to the sensor to test.')
    CONF.register_cli_opt(sensor_test_opt)

    st2_webhook_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='Host for the st2 webhook endpoint.'),
        cfg.IntOpt('port', default='6000', help='Port for the st2 webhook endpoint.'),
        cfg.StrOpt('url', default='/webhooks/st2/', help='URL of the st2 webhook endpoint.')
    ]
    CONF.register_opts(st2_webhook_opts, group='st2_webhook_sensor')

    generic_webhook_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='Host for the generic webhook endpoint.'),
        cfg.IntOpt('port', default='6001', help='Port for the generic webhook endpoint.'),
        cfg.StrOpt('url', default='/webhooks/generic/', help='URL of the st2 webhook endpoint.')
    ]
    CONF.register_opts(generic_webhook_opts, group='generic_webhook_sensor')


def _register_rules_engine_opts():
    logging_opts = [
        cfg.StrOpt('logging', default='conf/logging.rulesengine.conf',
                   help='Location of the logging configuration file.')
    ]
    CONF.register_opts(logging_opts, group='rulesengine')


def register_opts():
    _register_common_opts()
    _register_reactor_opts()
    _register_rules_engine_opts()


register_opts()


def parse_args(args=None):
    CONF(args=args)
