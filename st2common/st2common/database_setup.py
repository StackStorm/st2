# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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

from __future__ import absolute_import
from oslo_config import cfg

from st2common.models import db
from st2common.persistence import db_init

__all__ = ["db_config", "db_setup", "db_teardown"]


def db_config():
    username = getattr(cfg.CONF.database, "username", None)
    password = getattr(cfg.CONF.database, "password", None)

    return {
        "db_name": cfg.CONF.database.db_name,
        "db_host": cfg.CONF.database.host,
        "db_port": cfg.CONF.database.port,
        "username": username,
        "password": password,
        "tls": cfg.CONF.database.tls,
        "tls_certificate_key_file": cfg.CONF.database.tls_certificate_key_file,
        "tls_certificate_key_file_password": cfg.CONF.database.tls_certificate_key_file_password,
        "tls_allow_invalid_certificates": cfg.CONF.database.tls_allow_invalid_certificates,
        "tls_ca_file": cfg.CONF.database.tls_ca_file,
        "tls_allow_invalid_hostnames": cfg.CONF.database.tls_allow_invalid_hostnames,
        "ssl_cert_reqs": cfg.CONF.database.ssl_cert_reqs,  # deprecated
        "authentication_mechanism": cfg.CONF.database.authentication_mechanism,
        "ssl_match_hostname": cfg.CONF.database.ssl_match_hostname,  # deprecated
    }


def db_setup(ensure_indexes=True):
    """
    Creates the database and indexes (optional).
    """
    db_cfg = db_config()
    db_cfg["ensure_indexes"] = ensure_indexes
    connection = db_init.db_setup_with_retry(**db_cfg)
    return connection


def db_teardown():
    """
    Disconnects from the database.
    """
    return db.db_teardown()
