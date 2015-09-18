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

from pecan import load_app
from oslo_config import cfg

from st2api import config  # noqa
from st2common import log as logging
from st2common.persistence import db_init


cfg.CONF(args=['--config-file', '/etc/st2/st2.conf'])

logging.setup(cfg.CONF.api.logging)

username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
db_init.db_setup_with_retry(cfg.CONF.database.db_name, cfg.CONF.database.host,
                            cfg.CONF.database.port, username=username, password=password)

pecan_config = {
    'app': {
        'root': 'st2api.controllers.root.RootController',
        'modules': ['st2api'],
        'debug': cfg.CONF.api_pecan.debug,
        'errors': {'__force_dict__': True}
    }
}

application = load_app(pecan_config)
