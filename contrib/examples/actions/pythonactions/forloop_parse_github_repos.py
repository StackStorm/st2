from bs4 import BeautifulSoup

from st2common.runners.base_action import Action


class ParseGithubRepos(Action):
    def run(self, content):
        try:
            soup = BeautifulSoup(content, 'html.parser')
            repo_list = soup.find_all("h3")
            output = {}

            for each_item in repo_list:
                repo_half_url = each_item.find("a")['href']
                repo_name = repo_half_url.split("/")[-1]
                repo_url = "https://github.com" + repo_half_url
                output[repo_name] = repo_url
        except Exception as e:
            raise Exception("Could not parse data: {}".format(str(e)))

        return (True, output)
