import json

from st2common.runners.base_action import Action


class LoadAndPrintFixtureAction(Action):
    def run(self, file_path: str):
        with open(file_path, "r") as fp:
            content = fp.read()

        data = json.loads(content)
        return data
