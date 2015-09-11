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
st2api configuration / wsgi entry point file for gunicorn.
"""

# Note: We need this import otherwise pecan will try to import from local, not global cmd package
from __future__ import absolute_import

import os

from oslo_config import cfg

from st2api import config  # noqa
from st2common.service_setup import setup as common_setup

__all__ = [
    'app'
]

DEFAULT_ST2_CONFIG_PATH = '/etc/st2/st2.conf'
ST2_CONFIG_PATH = os.environ.get('ST2_CONFIG_PATH', DEFAULT_ST2_CONFIG_PATH)

CONFIG_ARGS = ['--config-file', ST2_CONFIG_PATH]
common_setup(service='api', config=config, setup_db=True, register_mq_exchanges=True,
             register_signal_handlers=False, register_internal_trigger_types=True,
             config_args=CONFIG_ARGS)

app = {
    'root': 'st2api.controllers.root.RootController',
    'modules': ['st2api'],
    'debug': cfg.CONF.api_pecan.debug,
    'errors': {'__force_dict__': True}
}
