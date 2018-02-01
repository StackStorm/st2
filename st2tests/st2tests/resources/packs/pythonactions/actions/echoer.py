from st2common.runners.base_action import Action


class Echoer(Action):
    def run(self, action_input):
        return {'action_input': action_input}
