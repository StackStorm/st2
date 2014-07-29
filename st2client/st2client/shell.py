"""
Command-line interface to Stanley
"""

import sys
import argparse
import logging

from st2client import models
from st2client.client import Client
from st2client.commands import resource
from st2client.commands import action
from st2client.commands import datastore


LOG = logging.getLogger(__name__)


class Shell(object):

    def __init__(self):

        # Set up of endpoints is delayed until program is run.
        self.client = None

        # Set up the main parser.
        self.parser = argparse.ArgumentParser(
            description='TODO: Add description for the CLI here.')

        # Set up general program options.
        self.parser.add_argument(
            '--url',
            action='store',
            dest='url',
            default=None,
            help='Base URL for the API servers. Assumes all servers uses the '
                 'same base URL and default ports are used. Get ST2_BASE_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--action-url',
            action='store',
            dest='action_url',
            default=None,
            help='URL for the Action API server. Get ST2_ACTION_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--reactor-url',
            action='store',
            dest='reactor_url',
            default=None,
            help='URL for the Reactor API server. Get ST2_REACTOR_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--datastore-url',
            action='store',
            dest='datastore_url',
            default=None,
            help='URL for the Datastore API server. Get ST2_DATASTORE_URL'
                 'from the environment variables by default.'
        )

        # Set up list of commands and subcommands.
        self.subparsers = self.parser.add_subparsers()
        self.commands = dict()

        self.commands['key'] = datastore.KeyValuePairBranch(
            'TODO: Put description of key value pair here.',
            self, self.subparsers)

        self.commands['trigger'] = resource.ResourceBranch(
            models.Trigger,
            'TODO: Put description of trigger here.',
            self, self.subparsers)

        self.commands['rule'] = resource.ResourceBranch(
            models.Rule,
            'TODO: Put description of rule here.',
            self, self.subparsers)

        self.commands['action'] = action.ActionBranch(
            'TODO: Put description of action here.',
            self, self.subparsers)
        self.commands['run'] = action.ActionExecuteCommand(
            models.Action, self, self.subparsers,
            name='run', add_help=False)
        self.commands['execution'] = action.ActionExecutionBranch(
            'TODO: Put description of action execution here.',
            self, self.subparsers)

    def get_client(self, args):
        endpoints = dict()
        if args.url:
            endpoints['base_url'] = args.url
        if args.action_url:
            endpoints['action_url'] = args.action_url
        if args.reactor_url:
            endpoints['reactor_url'] = args.reactor_url
        if args.datastore_url:
            endpoints['datastore_url'] = args.datastore_url
        return Client(**endpoints)

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
            print 'ERROR: %s\n' % e.message
            return 1


def main(argv=sys.argv[1:]):
    return Shell().run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
