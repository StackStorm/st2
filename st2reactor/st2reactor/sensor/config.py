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

from oslo_config import cfg, types

from st2common import config as st2cfg
from st2common.constants.sensors import DEFAULT_PARTITION_LOADER
from st2common.constants.system import VERSION_STRING

CONF = cfg.CONF


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)


def register_opts(ignore_errors=False):
    _register_common_opts(ignore_errors=ignore_errors)
    _register_sensor_container_opts(ignore_errors=ignore_errors)


def get_logging_config_path():
    return cfg.CONF.sensorcontainer.logging


def _register_common_opts(ignore_errors=False):
    st2cfg.register_opts(ignore_errors=ignore_errors)


def _register_sensor_container_opts(ignore_errors=False):
    logging_opts = [
        cfg.StrOpt('logging', default='conf/logging.sensorcontainer.conf',
                   help='location of the logging.conf file')
    ]
    st2cfg.do_register_opts(logging_opts, group='sensorcontainer', ignore_errors=ignore_errors)

    partition_opts = [
        cfg.StrOpt('sensor_node_name', default='sensornode1',
                   help='name of the sensor node.'),
        cfg.Opt('partition_provider', type=types.Dict(value_type=types.String()),
                default={'name': DEFAULT_PARTITION_LOADER},
                help='Provider of sensor node partition config.')
    ]
    st2cfg.do_register_opts(partition_opts, group='sensorcontainer', ignore_errors=ignore_errors)

    sensor_test_opt = cfg.StrOpt('sensor-ref', help='Only run sensor with the provided reference. \
        Value is of the form pack.sensor-name.')
    st2cfg.do_register_cli_opts(sensor_test_opt, ignore_errors=ignore_errors)


register_opts(ignore_errors=True)
