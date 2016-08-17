# Python action which uses the same module name as built-in Python module
# (test)

from st2actions.runners.pythonrunner import Action


class TestAction(Action):
    def run(self):
        return 'test action'
