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

from oslo_config import cfg

import st2common.config as common_config
from st2common.constants.system import VERSION_STRING
from st2common.constants.garbage_collection import DEFAULT_COLLECTION_INTERVAL
common_config.register_opts()

CONF = cfg.CONF


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)


def register_opts():
    _register_common_opts()
    _register_garbage_collector_opts()


def get_logging_config_path():
    return cfg.CONF.garbagecollector.logging


def _register_common_opts():
    common_config.register_opts()


def _register_garbage_collector_opts():
    logging_opts = [
        cfg.StrOpt('logging', default='conf/logging.garbagecollector.conf',
                   help='Location of the logging configuration file.')
    ]
    CONF.register_opts(logging_opts, group='garbagecollector')

    common_opts = [
        cfg.IntOpt('collection_interval', default=DEFAULT_COLLECTION_INTERVAL,
                   help='How often to check database for old data and perform garbage collection.')
    ]
    CONF.register_opts(common_opts, group='garbagecollector')

    ttl_opts = [
        cfg.IntOpt('action_executions_ttl', default=None,
                   help=('Action executions older than this value (days) will be automatically '
                         'deleted.')),
        cfg.IntOpt('trigger_instances_ttl', default=None,
                   help=('Trigger instances older than this value (days) will be automatically '
                         'deleted.'))
    ]
    CONF.register_opts(ttl_opts, group='garbagecollector')

register_opts()
