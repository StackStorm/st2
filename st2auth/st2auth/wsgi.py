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

import os

from pecan import load_app
from oslo_config import cfg

from st2auth import config  # noqa
config.register_opts()
from st2common import log as logging
from st2common.persistence import db_init


cfg.CONF(args=['--config-file', os.environ.get('ST2_CONFIG_PATH', '/etc/st2/st2.conf')])

logging.setup(cfg.CONF.auth.logging)

username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
db_init.db_setup_with_retry(cfg.CONF.database.db_name, cfg.CONF.database.host,
                            cfg.CONF.database.port, username=username, password=password,
                            ssl=cfg.CONF.database.ssl, ssl_keyfile=cfg.CONF.database.ssl_keyfile,
                            ssl_certfile=cfg.CONF.database.ssl_certfile,
                            ssl_cert_reqs=cfg.CONF.database.ssl_cert_reqs,
                            ssl_ca_certs=cfg.CONF.database.ssl_ca_certs,
                            ssl_match_hostname=cfg.CONF.database.ssl_match_hostname)

pecan_config = {
    'app': {
        'root': 'st2auth.controllers.root.RootController',
        'modules': ['st2auth'],
        'debug': cfg.CONF.auth.debug,
        'errors': {'__force_dict__': True}
    }
}

application = load_app(pecan_config)
