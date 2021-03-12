import json

from st2common.runners.base_action import Action


class JsonStringToObject(Action):
    def run(self, json_str):
        return json.loads(json_str)
