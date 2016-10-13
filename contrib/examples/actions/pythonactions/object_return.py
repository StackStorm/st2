from st2common.runners.base_action import Action


class ObjectReturnAction(Action):

    def run(self):
        return {'a': 'b', 'c': {'d': 'e', 'f': 1, 'g': True}}
