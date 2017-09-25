from st2common.runners.base_action import Action


class Test(object):
    foo = 'bar'


class NonSimpleTypeAction(Action):
    def run(self):
        result = [
            {'a': '1'},
            {'c': 2, 'h': 3},
            {'e': Test()}
        ]
        return result
