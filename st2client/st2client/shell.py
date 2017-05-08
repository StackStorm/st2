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
Command-line interface to StackStorm.
"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import argcomplete
import argparse
import logging

import six

from st2client import __version__
from st2client import models
from st2client.base import BaseCLIApp
from st2client.commands import auth
from st2client.commands import action
from st2client.commands import action_alias
from st2client.commands import keyvalue
from st2client.commands import pack
from st2client.commands import policy
from st2client.commands import resource
from st2client.commands import sensor
from st2client.commands import trace
from st2client.commands import trigger
from st2client.commands import triggerinstance
from st2client.commands import timer
from st2client.commands import webhook
from st2client.commands import rule
from st2client.commands import rule_enforcement
from st2client.commands import rbac
from st2client.config import set_config
from st2client.exceptions.operations import OperationFailureException
from st2client.utils.logging import LogLevelFilter, set_log_level_for_all_loggers
from st2client.commands.auth import TokenCreateCommand
from st2client.commands.auth import LoginCommand
from st2client.commands.auth import WhoamiCommand


__all__ = [
    'Shell'
]

LOGGER = logging.getLogger(__name__)

CLI_DESCRIPTION = 'CLI for StackStorm event-driven automation platform. https://stackstorm.com'


class Shell(BaseCLIApp):
    LOG = LOGGER

    SKIP_AUTH_CLASSES = [
        TokenCreateCommand.__name__,
        LoginCommand.__name__,
        WhoamiCommand.__name__
    ]

    def __init__(self):
        # Set up of endpoints is delayed until program is run.
        self.client = None

        # Set up the main parser.
        self.parser = argparse.ArgumentParser(description=CLI_DESCRIPTION)

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
            help='Base URL for the API servers. Assumes all servers use the '
                 'same base URL and default ports are used. Get ST2_BASE_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--auth-url',
            action='store',
            dest='auth_url',
            default=None,
            help='URL for the authentication service. Get ST2_AUTH_URL'
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
            help='API version to use. Get ST2_API_VERSION'
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
            '--config-file',
            action='store',
            dest='config_file',
            default=None,
            help='Path to the CLI config file'
        )

        self.parser.add_argument(
            '--print-config',
            action='store_true',
            dest='print_config',
            default=False,
            help='Parse the config file and print the values'
        )

        self.parser.add_argument(
            '--skip-config',
            action='store_true',
            dest='skip_config',
            default=False,
            help='Don\'t parse and use the CLI config file'
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

        self.commands['action'] = action.ActionBranch(
            'An activity that happens as a response to the external event.',
            self, self.subparsers)

        self.commands['action-alias'] = action_alias.ActionAliasBranch(
            'Action aliases.',
            self, self.subparsers)

        self.commands['auth'] = auth.TokenCreateCommand(
            models.Token, self, self.subparsers, name='auth')

        self.commands['api-key'] = auth.ApiKeyBranch(
            'API Keys.',
            self, self.subparsers)

        self.commands['execution'] = action.ActionExecutionBranch(
            'An invocation of an action.',
            self, self.subparsers)

        self.commands['key'] = keyvalue.KeyValuePairBranch(
            'Key value pair is used to store commonly used configuration '
            'for reuse in sensors, actions, and rules.',
            self, self.subparsers)

        self.commands['login'] = auth.LoginCommand(
            models.Token, self, self.subparsers, name='login')

        self.commands['pack'] = pack.PackBranch(
            'A group of related integration resources: '
            'actions, rules, and sensors.',
            self, self.subparsers)

        self.commands['policy'] = policy.PolicyBranch(
            'Policy that is enforced on a resource.',
            self, self.subparsers)

        self.commands['policy-type'] = policy.PolicyTypeBranch(
            'Type of policy that can be applied to resources.',
            self, self.subparsers)

        self.commands['rule'] = rule.RuleBranch(
            'A specification to invoke an "action" on a "trigger" selectively '
            'based on some criteria.',
            self, self.subparsers)

        self.commands['run'] = action.ActionRunCommand(
            models.Action, self, self.subparsers, name='run', add_help=False)

        self.commands['runner'] = resource.ResourceBranch(
            models.RunnerType,
            'Runner is a type of handler for a specific class of actions.',
            self, self.subparsers, read_only=True, has_disable=True)

        self.commands['sensor'] = sensor.SensorBranch(
            'An adapter which allows you to integrate StackStorm with external system ',
            self, self.subparsers)

        self.commands['trace'] = trace.TraceBranch(
            'A group of executions, rules and triggerinstances that are related.',
            self, self.subparsers)

        self.commands['trigger'] = trigger.TriggerTypeBranch(
            'An external event that is mapped to a st2 input. It is the '
            'st2 invocation point.',
            self, self.subparsers)

        self.commands['trigger-instance'] = triggerinstance.TriggerInstanceBranch(
            'Actual instances of triggers received by st2.',
            self, self.subparsers)

        self.commands['webhook'] = webhook.WebhookBranch(
            'Webhooks.',
            self, self.subparsers)

        self.commands['whoami'] = auth.WhoamiCommand(
            models.Token, self, self.subparsers, name='whoami')

        self.commands['timer'] = timer.TimerBranch(
            'Timers.',
            self, self.subparsers)

        self.commands['rule-enforcement'] = rule_enforcement.RuleEnforcementBranch(
            'Models that represent enforcement of rules.',
            self, self.subparsers)

        # RBAC
        self.commands['role'] = rbac.RoleBranch(
            'RBAC roles.',
            self, self.subparsers)
        self.commands['role-assignment'] = rbac.RoleAssignmentBranch(
            'RBAC role assignments.',
            self, self.subparsers)

    def run(self, argv):
        debug = False

        # Provide autocomplete for shell
        argcomplete.autocomplete(self.parser)

        if '--print-config' in argv:
            # Hack because --print-config requires no command to be specified
            argv = argv + ['action', 'list']

        # Parse command line arguments.
        args = self.parser.parse_args(args=argv)

        print_config = args.print_config
        if print_config:
            self._print_config(args=args)
            return 3

        # Parse config and store it in the config module
        config = self._parse_config_file(args=args)
        set_config(config=config)

        # Setup client and run the command
        try:
            debug = getattr(args, 'debug', False)
            if debug:
                set_log_level_for_all_loggers(level=logging.DEBUG)

            # Set up client.
            self.client = self.get_client(args=args, debug=debug)

            # Execute command.
            args.func(args)

            return 0
        except OperationFailureException as e:
            if debug:
                self._print_debug_info(args=args)
            return 2
        except Exception as e:
            # We allow exception to define custom exit codes
            exit_code = getattr(e, 'exit_code', 1)

            print('ERROR: %s\n' % e)
            if debug:
                self._print_debug_info(args=args)

            return exit_code

    def _print_config(self, args):
        config = self._parse_config_file(args=args)

        for section, options in six.iteritems(config):
            print('[%s]' % (section))

            for name, value in six.iteritems(options):
                print('%s = %s' % (name, value))


def setup_logging(argv):
    debug = '--debug' in argv

    root = LOGGER
    root.setLevel(logging.WARNING)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(asctime)s  %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    if not debug:
        handler.addFilter(LogLevelFilter(log_levels=[logging.ERROR]))

    root.addHandler(handler)


def main(argv=sys.argv[1:]):
    setup_logging(argv)
    return Shell().run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
