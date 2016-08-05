import yaml

from st2actions.runners.pythonrunner import Action


class YamlStringToObject(Action):

    def run(self, yaml_str):
        return yaml.safe_load(yaml_str)
