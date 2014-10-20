"""
Command-line interface to Stanley
"""

from __future__ import print_function

import sys
import argparse
import logging
import traceback

from st2client import models
from st2client.client import Client
from st2client.commands import resource
from st2client.commands import access
from st2client.commands import action
from st2client.commands import datastore


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

        self.commands['trigger'] = resource.ResourceBranch(
            models.Trigger,
            'An external event that is mapped to a stanley input. It is the '
            'stanley invocation point.',
            self, self.subparsers)

        self.commands['rule'] = resource.ResourceBranch(
            models.Rule,
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

    def get_client(self, args):
        options = ['base_url', 'auth_url', 'api_url', 'cacert']
        kwargs = {opt: getattr(args, opt) for opt in options}
        return Client(**kwargs)

    def run(self, argv):
        try:
            # Parse command line arguments.
            args = self.parser.parse_args(args=argv)

            # Set up client.
            self.client = self.get_client(args)

            # Execute command.
            args.func(args)

            return 0
        except Exception as e:
            print('ERROR: %s\n' % e)

            debug = getattr(args, 'debug', False)
            if debug:
                traceback.print_exc()

            return 1


def main(argv=sys.argv[1:]):
    return Shell().run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
