import yaml

from st2common.runners.base_action import Action


class YamlStringToObject(Action):
    def run(self, yaml_str):
        return yaml.safe_load(yaml_str)
