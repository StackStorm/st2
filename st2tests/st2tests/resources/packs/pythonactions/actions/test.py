# Python action which uses the same module name as built-in Python module
# (test)

from __future__ import absolute_import
from st2common.runners.base_action import Action


class TestAction(Action):
    def run(self):
        return 'test action'
