# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six

from bs4 import BeautifulSoup

from st2common.runners.base_action import Action


class ParseGithubRepos(Action):
    def run(self, content):
        try:
            soup = BeautifulSoup(content, "html.parser")
            repo_list = soup.find_all("h3")
            output = {}

            for each_item in repo_list:
                repo_half_url = each_item.find("a")["href"]
                repo_name = repo_half_url.split("/")[-1]
                repo_url = "https://github.com" + repo_half_url
                output[repo_name] = repo_url
        except Exception as e:
            raise Exception("Could not parse data: {}".format(six.text_type(e)))

        return (True, output)
