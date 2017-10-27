import requests

from st2common.runners.base_action import Action


class ForloopGetGithubPage(Action):
    def run(self, url, page="1"):
        request = "{}?page={}".format(url, page)
        response = requests.get(request)

        if not response.ok:
            raise Exception("Could not request url: {}".format(request))

        return (True, response.content)
