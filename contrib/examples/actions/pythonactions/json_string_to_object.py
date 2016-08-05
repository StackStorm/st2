import json

from st2actions.runners.pythonrunner import Action


class JsonStringToObject(Action):

    def run(self, json_str):
        return json.loads(json_str)
