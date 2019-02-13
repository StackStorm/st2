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

from __future__ import absolute_import

import six

from oslo_config import cfg

from st2common import config
from st2common.services import coordination

"""
Tool which lists all the services registered in the service registry and their capabilities.
"""

def main(group_id=None):
    coordinator = coordination.get_coordinator()

    if not group_id:
        group_ids = list(coordinator.get_groups().get())

        print('Available groups:')
        for group_id in group_ids:
            print(' - %s' % (group_id))
        print('')
    else:
        group_ids = [group_id]

    for group_id in group_ids:
        print('Members in group "%s":' % (group_id))
        member_ids = list(coordinator.get_members(group_id).get())

        for member_id in member_ids:
            capabilities = coordinator.get_member_capabilities(group_id, member_id).get()
            print(' - %s (capabilities=%s)' % (member_id, str(capabilities)))


def do_register_cli_opts(opts, ignore_errors=False):
    for opt in opts:
        try:
            cfg.CONF.register_cli_opt(opt)
        except:
            if not ignore_errors:
                raise


if __name__ == '__main__':
    cli_opts = [
        cfg.StrOpt('group-id', default=None,
                    help='If provided, only list members for that group.'),

    ]
    do_register_cli_opts(cli_opts)
    config.parse_args()

    main(group_id=cfg.CONF.group_id)
