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
Command-line interface to Stanley
"""

from __future__ import print_function

import os
import sys
import argparse
import logging
import traceback

from st2client import __version__
from st2client import models
from st2client.client import Client
from st2client.commands import resource
from st2client.commands import access
from st2client.commands import sensor
from st2client.commands import trigger
from st2client.commands import action
from st2client.commands import datastore
from st2client.commands import webhook
from st2client.commands import rule
from st2client.exceptions.operations import OperationFailureException


LOG = logging.getLogger(__name__)


class Shell(object):

    def __init__(self):
        # Set up of endpoints is delayed until program is run.
        self.client = None

        # Set up the main parser.
        self.parser = argparse.ArgumentParser(
            description='CLI for Stanley, an automation platform by '
                        'StackStorm. http://stackstorm.com')

        # Set up general program options.
        self.parser.add_argument(
            '--version',
            action='version',
            version='%(prog)s {version}'.format(version=__version__))

        self.parser.add_argument(
            '--url',
            action='store',
            dest='base_url',
            default=None,
            help='Base URL for the API servers. Assumes all servers uses the '
                 'same base URL and default ports are used. Get ST2_BASE_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--auth-url',
            action='store',
            dest='auth_url',
            default=None,
            help='URL for the autentication service. Get ST2_AUTH_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--api-url',
            action='store',
            dest='api_url',
            default=None,
            help='URL for the API server. Get ST2_API_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--api-version',
            action='store',
            dest='api_version',
            default=None,
            help='API version to sue. Get ST2_API_VERSION'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--cacert',
            action='store',
            dest='cacert',
            default=None,
            help='Path to the CA cert bundle for the SSL endpoints. '
                 'Get ST2_CACERT from the environment variables by default. '
                 'If this is not provided, then SSL cert will not be verified.'
        )

        self.parser.add_argument(
            '--debug',
            action='store_true',
            dest='debug',
            default=False,
            help='Enable debug mode'
        )

        # Set up list of commands and subcommands.
        self.subparsers = self.parser.add_subparsers()
        self.commands = dict()

        self.commands['auth'] = access.TokenCreateCommand(
            models.Token, self, self.subparsers, name='auth')

        self.commands['key'] = datastore.KeyValuePairBranch(
            'Key value pair is used to store commonly used configuration '
            'for reuse in sensors, actions, and rules.',
            self, self.subparsers)

        self.commands['sensor'] = sensor.SensorBranch(
            'An adapter which allows you to integrate Stanley with external system ',
            self, self.subparsers)

        self.commands['trigger'] = trigger.TriggerTypeBranch(
            'An external event that is mapped to a st2 input. It is the '
            'st2 invocation point.',
            self, self.subparsers)

        self.commands['rule'] = rule.RuleBranch(
            'A specification to invoke an "action" on a "trigger" selectively '
            'based on some criteria.',
            self, self.subparsers)

        self.commands['action'] = action.ActionBranch(
            'An activity that happens as a response to the external event.',
            self, self.subparsers)
        self.commands['runner'] = resource.ResourceBranch(
            models.RunnerType,
            'Runner is a type of handler for a specific class of actions.',
            self, self.subparsers, read_only=True)
        self.commands['run'] = action.ActionRunCommand(
            models.Action, self, self.subparsers, name='run', add_help=False)
        self.commands['execution'] = action.ActionExecutionBranch(
            'An invocation of an action.',
            self, self.subparsers)

        self.commands['webhook'] = webhook.WebhookBranch(
            'Webhooks.',
            self, self.subparsers)

    def get_client(self, args, debug=False):
        options = ['base_url', 'auth_url', 'api_url', 'api_version', 'cacert']
        kwargs = {opt: getattr(args, opt) for opt in options}
        kwargs['debug'] = debug
        return Client(**kwargs)

    def run(self, argv):
        debug = False
        try:
            # Parse command line arguments.
            args = self.parser.parse_args(args=argv)

            debug = getattr(args, 'debug', False)

            # Set up client.
            self.client = self.get_client(args=args, debug=debug)

            # Execute command.
            args.func(args)

            return 0
        except OperationFailureException as e:
            if debug:
                self._print_debug_info()
            return 2
        except Exception as e:
            print('ERROR: %s\n' % e)
            if debug:
                self._print_debug_info()
            return 1

    def _print_debug_info(self):
        # Print client settings
        self._print_client_settings()

        # Print exception traceback
        traceback.print_exc()

    def _print_client_settings(self):
        client = self.client

        if not client:
            return

        print('Client settings:')
        print('----------------')
        print('ST2_BASE_URL: %s' % (client.endpoints['base']))
        print('ST2_AUTH_URL: %s' % (client.endpoints['auth']))
        print('ST2_API_URL: %s' % (client.endpoints['api']))
        print('')
        print('Proxy settings:')
        print('---------------')
        print('HTTP_PROXY: %s' % (os.environ.get('HTTP_PROXY', '')))
        print('HTTPS_PROXY: %s' % (os.environ.get('HTTPS_PROXY', '')))
        print('')


def main(argv=sys.argv[1:]):
    return Shell().run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
