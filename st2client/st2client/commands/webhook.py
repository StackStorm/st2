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

from st2client.commands import resource
from st2client.formatters import table
from st2client.models import Webhook


class WebhookBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(WebhookBranch, self).__init__(
            Webhook, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': WebhookListCommand,
                'get': WebhookGetCommand
            })


class WebhookListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['url', 'type', 'description']

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)

        for instance in instances:
            instance.url = instance.parameters['url']

        instances = sorted(instances, key=lambda k: k.url)

        if args.json or args.yaml:
            self.print_output(instances, table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              json=args.json, yaml=args.yaml)
        else:
            self.print_output(instances, table.MultiColumnTable,
                              attributes=args.attr, widths=args.width)


class WebhookGetCommand(resource.ResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['type', 'description']

    pk_argument_name = 'url'
