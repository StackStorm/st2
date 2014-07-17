"""
Command-line interface to Stanley
"""

import sys
import argparse
import logging

from st2client import utils
from st2client.client import Client
from st2client.commands import resource
from st2client.commands import action
from st2client.commands import datastore
from st2client.models import reactor


LOG = logging.getLogger(__name__)


class Shell(object):

    def __init__(self):

        # Set up of endpoints is delayed until program is run.
        self.endpoints = {}
        self.client = None

        # Set up the main parser.
        self.parser = argparse.ArgumentParser(
            description='TODO: Add description for the CLI here.',
            add_help=False)

        # Set up general program options.
        self.parser.add_argument(
            '--url',
            action='store',
            dest='url',
            default=utils.env('ST2_URL', default='http://localhost'),
            help='Base URL for the API servers. Assumes all servers uses the '
                 'same base URL and default ports are used.'
        )

        self.parser.add_argument(
            '--action-url',
            action='store',
            dest='action_url',
            default=utils.env('ST2_ACTION_URL', default=None),
            help='URL for the Action API server.'
        )

        self.parser.add_argument(
            '--reactor-url',
            action='store',
            dest='reactor_url',
            default=utils.env('ST2_REACTOR_URL', default=None),
            help='URL for the Reactor API server.'
        )

        self.parser.add_argument(
            '--datastore-url',
            action='store',
            dest='datastore_url',
            default=utils.env('ST2_DATASTORE_URL', default=None),
            help='URL for the Datastore API server.'
        )

        # Set up list of commands and subcommands.
        self.subparsers = self.parser.add_subparsers()
        self.commands = dict()
        self.commands['help'] = resource.ResourceHelpCommand(
            self.commands, None, self, self.subparsers,
            parent_parser=self.parser)
        self.commands['action'] = action.ActionBranch(
            'TODO: Put description of action here.',
            self, self.subparsers)
        self.commands['key'] = datastore.KeyValuePairBranch(
            'TODO: Put description of key value pair here.',
            self, self.subparsers)
        self.commands['execution'] = action.ActionExecutionBranch(
            'TODO: Put description of action execution here.',
            self, self.subparsers)
        self.commands['rule'] = resource.ResourceBranch(
            reactor.Rule,
            'TODO: Put description of rule here.',
            self, self.subparsers)
        self.commands['trigger'] = resource.ResourceBranch(
            reactor.Trigger,
            'TODO: Put description of trigger here.',
            self, self.subparsers)

    def run(self, argv):
        # Parse command line arguments.
        args = self.parser.parse_args()

        # Set up client.
        self.endpoints['action'] = (
            args.action_url if args.action_url else '%s:9101' % args.url)
        self.endpoints['reactor'] = (
            args.reactor_url if args.reactor_url else '%s:9102' % args.url)
        self.endpoints['datastore'] = (
            args.datastore_url if args.datastore_url else '%s:9103' % args.url)
        self.client = Client(self.endpoints)

        # Execute command.
        args.func(args)


def main(argv=sys.argv[1:]):
    return Shell().run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
