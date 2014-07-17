import logging
import unittest2

from st2client import shell


LOG = logging.getLogger(__name__)


class TestShell(unittest2.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestShell, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()

    def _validate_parser(self, args_list):
        for args in args_list:
            ns = self.shell.parser.parse_args(args)
            func = self.shell.commands[args[0]].commands[args[1]].run_and_print
            self.assertEqual(ns.func, func)

    def test_trigger(self):
        args_list = [
            ['trigger', 'list'],
            ['trigger', 'get', 'abc'],
            ['trigger', 'create', '/tmp/trigger.json'],
            ['trigger', 'update', '123', '/tmp/trigger.json'],
            ['trigger', 'delete', 'abc']
        ]
        self._validate_parser(args_list)

    def test_rule(self):
        args_list = [
            ['rule', 'list'],
            ['rule', 'get', 'abc'],
            ['rule', 'create', '/tmp/rule.json'],
            ['rule', 'update', '123', '/tmp/rule.json'],
            ['rule', 'delete', 'abc']
        ]
        self._validate_parser(args_list)

    def test_action(self):
        args_list = [
            ['action', 'list'],
            ['action', 'get', 'abc'],
            ['action', 'create', '/tmp/action.json'],
            ['action', 'update', '123', '/tmp/action.json'],
            ['action', 'delete', 'abc'],
            ['action', 'execute', 'abc', '-r', 'command="uname =a"']
        ]
        self._validate_parser(args_list)

    def test_action_execution(self):
        args_list = [
            ['execution', 'list'],
            ['execution', 'get', '123'],
        ]
        self._validate_parser(args_list)

    def test_key(self):
        args_list = [
            ['key', 'list'],
            ['key', 'get', 'abc'],
            ['key', 'create', 'abc', '123'],
            ['key', 'update', 'abc', '456'],
            ['key', 'delete', 'abc'],
            ['key', 'load', '/tmp/keys.json']
        ]
        self._validate_parser(args_list)
