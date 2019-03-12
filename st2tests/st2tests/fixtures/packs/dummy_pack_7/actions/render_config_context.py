from st2common.runners.base_action import Action


class PrintPythonVersionAction(Action):

    def run(self, value1):
        return {"context_value": value1}
