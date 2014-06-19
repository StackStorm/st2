# -*- coding: utf-8 -*-
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging

from st2client.commands import Command


LOG = logging.getLogger(__name__)


class HelpCommand(Command):

    def __init__(self, subparsers, commands, parent_parser=None):
        super(HelpCommand, self).__init__(
            'help', 'Print usage information for the given command.',
            subparsers, parent_parser=parent_parser)

        # If parent parser is the top level parser, set the command argument to
        # optional so that running "prog help" will return the program's help
        # message instead of throwing the "too few arguments" error.
        nargs = '?' if self.parent_parser and self.parent_parser.prog else None
        self.parser.add_argument('command', help='Name of the command.', nargs=nargs)

        # Registers this help command in the command list so "prog help help" will
        # return the help message for this help command.
        self.commands = commands
        self.commands['help'] = self

    def run(self, args):
        if args.command:
            command = self.commands[args.command]
            command.parser.print_help()
        else:
            if self.parent_parser and self.parent_parser.prog:
                self.parent_parser.print_help()
            else:
                self.parser.print_help()
        print
