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
# limitations under the License.A

"""
Module contain database set up and teardown related functionality.
"""

from oslo_config import cfg

from st2common.models import db
from st2common.persistence import db_init

__all__ = [
    'db_setup',
    'db_teardown'
]


def db_setup(ensure_indexes=True):
    username = getattr(cfg.CONF.database, 'username', None)
    password = getattr(cfg.CONF.database, 'password', None)

    connection = db_init.db_setup_with_retry(
        db_name=cfg.CONF.database.db_name, db_host=cfg.CONF.database.host,
        db_port=cfg.CONF.database.port, username=username, password=password,
        ensure_indexes=ensure_indexes,
        ssl=cfg.CONF.database.ssl, ssl_keyfile=cfg.CONF.database.ssl_keyfile,
        ssl_certfile=cfg.CONF.database.ssl_certfile,
        ssl_cert_reqs=cfg.CONF.database.ssl_cert_reqs,
        ssl_ca_certs=cfg.CONF.database.ssl_ca_certs,
        ssl_match_hostname=cfg.CONF.database.ssl_match_hostname)
    return connection


def db_teardown():
    return db.db_teardown()
