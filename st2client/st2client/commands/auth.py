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

import getpass
import logging

from st2client.commands import resource
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class TokenCreateCommand(resource.ResourceCommand):

    display_attributes = ['user', 'token', 'expiry']

    def __init__(self, resource, *args, **kwargs):

        kwargs['has_token_opt'] = False

        super(TokenCreateCommand, self).__init__(
            resource, kwargs.pop('name', 'create'),
            'Authenticate user and aquire access token.',
            *args, **kwargs)

        self.parser.add_argument('username',
                                 help='Name of the user to authenticate.')

        self.parser.add_argument('-p', '--password', dest='password',
                                 help='Password for the user. If password is not provided, '
                                      'it will be prompted.')
        self.parser.add_argument('-l', '--ttl', type=int, dest='ttl', default=None,
                                 help='The life span of the token in seconds. '
                                      'Max TTL configured by the admin supersedes this.')
        self.parser.add_argument('-t', '--only-token', action='store_true', dest='only_token',
                                 default=False,
                                 help='Only print token to the console on successful '
                                      'authentication.')

    def run(self, args, **kwargs):
        if not args.password:
            args.password = getpass.getpass()
        instance = self.resource(ttl=args.ttl) if args.ttl else self.resource()
        return self.manager.create(instance, auth=(args.username, args.password), **kwargs)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)

        if args.only_token:
            print(instance.token)
        else:
            self.print_output(instance, table.PropertyValueTable,
                              attributes=self.display_attributes, json=args.json)
