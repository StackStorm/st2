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
# limitations under the License.

from __future__ import absolute_import
import sys

from st2common import config
from st2common import log as logging
from st2common.database_setup import db_config
from st2common.models.db import db_cleanup as db_cleanup_func
from st2common.persistence.db_init import db_func_with_retry
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown

__all__ = ["db_cleanup", "db_cleanup_with_retry", "main"]

LOG = logging.getLogger(__name__)


def db_cleanup():
    """
    Drops the database.
    """
    db_cfg = db_config()
    connection = db_cleanup_with_retry(**db_cfg)
    return connection


def db_cleanup_with_retry(
    db_name,
    db_host,
    db_port,
    username=None,
    password=None,
    ssl=False,
    ssl_keyfile=None,
    ssl_certfile=None,
    ssl_cert_reqs=None,
    ssl_ca_certs=None,
    authentication_mechanism=None,
    ssl_match_hostname=True,
):
    """
    This method is a retry version of db_cleanup.
    """
    return db_func_with_retry(
        db_cleanup_func,
        db_name,
        db_host,
        db_port,
        username=username,
        password=password,
        ssl=ssl,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
        authentication_mechanism=authentication_mechanism,
        ssl_match_hostname=ssl_match_hostname,
    )


def setup(argv):
    common_setup(
        config=config,
        setup_db=False,
        register_mq_exchanges=False,
        register_internal_trigger_types=False,
    )


def teardown():
    common_teardown()


def main(argv):
    setup(argv)
    db_cleanup()
    teardown()


# This script registers actions and rules from content-packs.
if __name__ == "__main__":
    main(sys.argv[1:])
