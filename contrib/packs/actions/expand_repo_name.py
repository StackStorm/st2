#!/usr/bin/env python

# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from st2actions.runners.pythonrunner import Action


class ExpandRepoName(Action):
    def run(self, repo_name):
        """Returns the data required to install packs from repo_name.

        Keyword arguments:
          repo_name -- The Reposistory name to look up in the Packs config.yaml.

        Returns: A Dict containing repo_url and subtree.

        Raises:
          ValueError: If the supplied repo_name is present (or complete).
        """
        # Set up the results object
        results = {}

        try:
            results['repo_url'] = self.config["repositories"][repo_name]["repo"]
            results['subtree'] = self.config["repositories"][repo_name]["subtree"]
        except KeyError:
            raise ValueError("Missing repositories config for '%s'" % repo_name)
        else:
            return results
