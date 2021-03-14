import orjson

from st2common.runners.base_action import Action


class LoadAndPrintFixtureAction(Action):
    def run(self, file_path: str):
        with open(file_path, "r") as fp:
            content = fp.read()

        data = orjson.loads(content)
        return data
