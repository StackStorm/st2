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

from st2client.models.action_alias import ActionAlias
from st2client.commands import resource
from st2client.commands.resource import add_auth_token_to_kwargs_from_cli
from st2client.formatters import table

__all__ = [
    'ActionAliasBranch'
]


class ActionAliasBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionAliasBranch, self).__init__(
            ActionAlias, description, app, subparsers,
            parent_parser=parent_parser, read_only=True,
            commands={
                'list': ActionAliasListCommand
            })


class ActionAliasListCommand(resource.ResourceCommand):
    display_attributes = ['ref', 'pack', 'name', 'description', 'enabled']
    attribute_transform_functions = {}

    def __init__(self, resource, *args, **kwargs):
        super(ActionAliasListCommand, self).__init__(
            resource, 'list', 'Get the list of the %s' %
            (resource.get_plural_display_name().lower()),
            *args, **kwargs)

        # Display options
        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=self.display_attributes,
                                 help=('List of attributes to include in the '
                                       'output. "all" will return all '
                                       'attributes.'))
        self.parser.add_argument('-w', '--width', nargs='+', type=int,
                                 default=None,
                                 help=('Set the width of columns in output.'))

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.query(**kwargs)

    def run_and_print(self, args, **kwargs):
        result = self.run(args, **kwargs)
        self.print_output(result, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json,
                          attribute_transform_functions=self.attribute_transform_functions)
