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
from st2common.constants.system import VERSION_STRING
common_config.register_opts()

CONF = cfg.CONF


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)


def register_opts():
    _register_common_opts()
    _register_rules_engine_opts()


def get_logging_config_path(service='rulesengine'):
    return cfg.CONF.rulesengine.logging


def _register_common_opts():
    common_config.register_opts()


def _register_rules_engine_opts():
    logging_opts = [
        cfg.StrOpt('logging', default='conf/logging.rulesengine.conf',
                   help='Location of the logging configuration file.')
    ]
    CONF.register_opts(logging_opts, group='rulesengine')

    timer_opts = [
        cfg.StrOpt('local_timezone', default='America/Los_Angeles',
                   help='Timezone pertaining to the location where st2 is run.')
    ]
    CONF.register_opts(timer_opts, group='timer')


register_opts()
