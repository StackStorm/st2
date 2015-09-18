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

import mongoengine

from oslo_config import cfg
from retrying import retry

from st2common import log as logging
from st2common.models.db import db_setup

__all__ = [
    'db_setup_with_retry'
]

LOG = logging.getLogger(__name__)

DB_CONNRETRY_MAX_DELAY = cfg.CONF.database.connection_retry_max_delay_m * 60 * 1000
DB_CONNRETRY_EXP_BACK_OFF_MAX = cfg.CONF.database.connection_retry_backoff_max_s * 1000
DB_CONNRETRY_EXP_BACK_OFF_MUL = cfg.CONF.database.connection_retry_backoff_mul * 1000


def _retry_if_connection_error(error):
    # Ideally we only want to retry on failure to connect to DB as opposed to
    # bad connection details. However, mongoengine raises a ConnectionError for
    # a few different cases and the only option would be to parse the error msg.
    # Ideally, a special execption or atleast some exception code.
    # If this does become an issue look for "Cannot connect to database" at the
    # start of error msg.
    is_connection_error = isinstance(error, mongoengine.connection.ConnectionError)
    if is_connection_error:
        LOG.warn('Retry on ConnectionError - %s', error)
    return is_connection_error


@retry(retry_on_exception=_retry_if_connection_error,
       wait_exponential_multiplier=DB_CONNRETRY_EXP_BACK_OFF_MUL,
       wait_exponential_max=DB_CONNRETRY_EXP_BACK_OFF_MAX,
       stop_max_delay=DB_CONNRETRY_MAX_DELAY)
def db_setup_with_retry(db_name, db_host, db_port, username=None, password=None,
                        ensure_indexes=True):
    """
    This method is a retry version of db_setup.
    """
    return db_setup(db_name, db_host, db_port, username=username, password=password,
                    ensure_indexes=ensure_indexes)
