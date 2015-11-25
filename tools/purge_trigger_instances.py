#!/usr/bin/env python
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

from datetime import datetime
import sys

from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2common.persistence.trigger import TriggerInstance
from st2common.util import isotime

LOG = logging.getLogger(__name__)
DELETED_COUNT = 0


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
                   help='Will delete trigger instances older than ' +
                   'this timestamp. ' +
                   'Example value: 2015-03-13T19:01:27.255542Z')
    ]
    _do_register_cli_opts(cli_opts)


def _purge_model(instance):
    try:
        TriggerInstance.delete(instance)
    except:
        LOG.exception('Exception deleting instance %s.', instance)
    else:
        global DELETED_COUNT
        DELETED_COUNT += 1


def purge_trigger_instances(timestamp=None):
    if not timestamp:
        LOG.error('Specify a valid timestamp to purge.')
        return

    LOG.info('Purging trigger instances older than timestamp: %s' %
             timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

    # XXX: Think about paginating this call.
    filters = {'occurrence_time__lt': isotime.parse(timestamp)}
    instances = TriggerInstance.query(**filters)

    LOG.info('#### Total number of trigger instances to delete: %d' % len(instances))

    # Purge execution and liveaction models now
    for instance in instances:
        _purge_model(instance)

    # Print stats
    LOG.info('#### Total trigger instances deleted: %d' % DELETED_COUNT)


def main():
    _register_cli_opts()
    common_setup(config=config, setup_db=True, register_mq_exchanges=True)

    # Get config values
    timestamp = cfg.CONF.timestamp
    action_ref = cfg.CONF.action_ref

    if not timestamp:
        LOG.error('Please supply a timestamp for purging models. Aborting.')
        return 1
    else:
        timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

    # Purge models.
    purge_trigger_instances(timestamp=timestamp, action_ref=action_ref)

    common_teardown()

if __name__ == '__main__':
    sys.exit(main())
