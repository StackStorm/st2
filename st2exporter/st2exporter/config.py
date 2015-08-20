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

"""
Configuration options registration and useful routines.
"""

from oslo_config import cfg

import st2common.config as common_config
from st2common.constants.system import VERSION_STRING
common_config.register_opts()

CONF = cfg.CONF


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)


def get_logging_config_path():
    return cfg.CONF.exporter.logging


dump_opts = [
    cfg.StrOpt('dump_dir', default='/opt/stackstorm/exports/',
               help='Directory to dump data to.')
]
CONF.register_opts(dump_opts, group='exporter')

logging_opts = [
    cfg.StrOpt('logging', default='conf/logging.exporter.conf',
               help='location of the logging.exporter.conf file')
]
CONF.register_opts(logging_opts, group='exporter')
