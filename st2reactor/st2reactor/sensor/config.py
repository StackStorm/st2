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

from st2common import config as st2cfg
from st2api import config as st2apicfg
from st2common.constants.system import VERSION_STRING
#st2cfg.register_opts()

CONF = cfg.CONF


def _register_common_opts():
    st2cfg.register_opts()


def _register_api_opts():
    st2apicfg.register_opts()


def _register_sensor_container_opts():
    logging_opts = [
        cfg.StrOpt('logging', default='conf/logging.sensorcontainer.conf',
                   help='location of the logging.conf file')
    ]
    CONF.register_opts(logging_opts, group='sensorcontainer')

    sensor_test_opt = cfg.StrOpt('sensor-name', help='Only run sensor with the provided name.')
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


def register_opts():
    _register_common_opts()
    _register_api_opts()
    _register_sensor_container_opts()


register_opts()


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)
