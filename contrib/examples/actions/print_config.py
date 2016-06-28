from pprint import pprint

from st2actions.runners.pythonrunner import Action


class PrintConfigAction(Action):
    def run(self):
        print('=========')
        pprint(self.config)
        print('=========')
