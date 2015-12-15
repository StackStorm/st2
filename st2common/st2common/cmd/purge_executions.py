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
A utility script that purges st2 executions older than certain
timestamp.

*** RISK RISK RISK. You will lose data. Run at your own risk. ***
"""

import copy
from datetime import datetime
import pytz

from mongoengine.errors import InvalidQueryError
from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution import ActionExecution
from st2common.util import isotime

LOG = logging.getLogger(__name__)

DONE_STATES = [action_constants.LIVEACTION_STATUS_SUCCEEDED,
               action_constants.LIVEACTION_STATUS_FAILED,
               action_constants.LIVEACTION_STATUS_TIMED_OUT,
               action_constants.LIVEACTION_STATUS_CANCELED]


def _do_register_cli_opts(opts, ignore_errors=False):
    for opt in opts:
        try:
            cfg.CONF.register_cli_opt(opt)
        except:
            if not ignore_errors:
                raise


def _register_cli_opts():
    cli_opts = [
        cfg.StrOpt('timestamp', default=None,
                   help='Will delete execution and liveaction models older than ' +
                   'this UTC timestamp. ' +
                   'Example value: 2015-03-13T19:01:27.255542Z.'),
        cfg.StrOpt('action-ref', default='',
                   help='action-ref to delete executions for.'),
        cfg.BoolOpt('purge-incomplete', default=False,
                    help='Purge all models irrespective of their ``status``.' +
                    'By default, only executions in completed states such as "succeeeded" ' +
                    ', "failed", "canceled" and "timed_out" are deleted.'),
    ]
    _do_register_cli_opts(cli_opts)


def purge_executions(timestamp=None, action_ref=None, purge_incomplete=False):
    if not timestamp:
        LOG.error('Specify a valid timestamp to purge.')
        return 1

    LOG.info('Purging executions older than timestamp: %s' %
             timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

    filters = {}

    if purge_incomplete:
        filters['start_timestamp__lt'] = isotime.parse(timestamp)
    else:
        filters['end_timestamp__lt'] = isotime.parse(timestamp)
        filters['start_timestamp__lt'] = isotime.parse(timestamp)
        filters['status'] = {"$in": DONE_STATES}

    exec_filters = copy.copy(filters)
    if action_ref:
        exec_filters['action__ref'] = action_ref

    liveaction_filters = copy.copy(filters)
    if action_ref:
        liveaction_filters['action'] = action_ref

    try:
        ActionExecution.delete_by_query(**exec_filters)
    except InvalidQueryError:
        LOG.exception('Bad query (%s) used to delete execution instances. ' +
                      'Please contact support.', exec_filters)
        return 2
    except:
        LOG.exception('Deletion of execution models failed for query with filters: %s.',
                      exec_filters)

    try:
        LiveAction.delete_by_query(**liveaction_filters)
    except InvalidQueryError:
        LOG.exception('Bad query (%s) used to delete liveaction instances. ' +
                      'Please contact support.', liveaction_filters)
        return 3
    except:
        LOG.exception('Deletion of liveaction models failed for query with filters: %s.',
                      liveaction_filters)

    zombie_execution_instances = len(ActionExecution.query(**exec_filters))
    zombie_liveaction_instances = len(LiveAction.query(**liveaction_filters))

    if (zombie_execution_instances > 0) or (zombie_liveaction_instances > 0):
        LOG.error('Zombie execution instances left: %d.', zombie_execution_instances)
        LOG.error('Zombie liveaction instances left: %s.', zombie_liveaction_instances)
    else:
        # Print stats
        LOG.info('#### All execution models less than timestamp %s were deleted.', timestamp)


def main():
    _register_cli_opts()
    common_setup(config=config, setup_db=True, register_mq_exchanges=False)

    # Get config values
    timestamp = cfg.CONF.timestamp
    action_ref = cfg.CONF.action_ref
    purge_incomplete = cfg.CONF.purge_incomplete

    if not timestamp:
        LOG.error('Please supply a timestamp for purging models. Aborting.')
        return 1
    else:
        timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        timestamp = timestamp.replace(tzinfo=pytz.UTC)

    # Purge models.
    try:
        return purge_executions(timestamp=timestamp, action_ref=action_ref,
                                purge_incomplete=purge_incomplete)
    finally:
        common_teardown()
