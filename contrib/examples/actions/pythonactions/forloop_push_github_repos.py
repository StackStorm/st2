from __future__ import print_function
from st2common.runners.base_action import Action


class PushGithubRepos(Action):
    def run(self, data_to_push):
        try:
            for each_item in data_to_push:
                # Push data to a service here
                print(str(each_item))
        except Exception as e:
            raise Exception("Process failed: {}".format(six.text_type(e)))

        return (True, "Data pushed successfully")
