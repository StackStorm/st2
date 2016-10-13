from pprint import pprint

from st2common.runners.base_action import Action


class PrintConfigAction(Action):
    def run(self):
        print('=========')
        pprint(self.config)
        print('=========')
