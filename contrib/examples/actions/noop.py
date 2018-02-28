from pprint import pprint

from st2common.runners.base_action import Action


class PrintParametersAction(Action):
    def run(self, **parameters):
        print('=========')
        pprint(parameters)
        print('=========')
