"""
Command-line interface to Stanley
"""

import sys
import argparse
import logging

from st2client.client import Client
from st2client.commands import help
from st2client.commands import resource
from st2client.commands import action
from st2client.models import reactor


LOG = logging.getLogger(__name__)


def main(argv=sys.argv[1:]):

    # set up main parser
    parser = argparse.ArgumentParser(
        description='TODO: Add description for the CLI here.',
        add_help=False)

    # set up connection
    endpoints = {
        'action': 'http://localhost:9101',
        'reactor': 'http://localhost:9102'
    }
    client = Client(endpoints)

    # set up commands
    subparsers = parser.add_subparsers()
    commands = dict()
    help.HelpCommand(subparsers, commands, parent_parser=parser)
    commands['action'] = action.ActionBranch(
        client.actions,
        'TODO: Put description of action here.',
        subparsers)
    commands['actionexecution'] = action.ActionExecutionBranch(
        client.executions,
        'TODO: Put description of action execution here.',
        subparsers)
    commands['rule'] = resource.ResourceBranch(
        reactor.Rule, client.rules,
        'TODO: Put description of rule here.',
        subparsers)
    commands['trigger'] = resource.ResourceBranch(
        reactor.Trigger, client.triggers,
        'TODO: Put description of trigger here.',
        subparsers, read_only=True)

    # parse arguments
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
