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

import sys
import requests
import json
import getopt
import argparse
import os
import yaml

from getpass import getpass
from st2actions.runners.pythonrunner import Action

class expand_repo_name(Action):
    def __init__(self, config=None):
        super(expand_repo_name, self).__init__(config=config)

    def run(self, repo_name):

        # Set up the results object
        results = {}

        try:
            results['repo_url'] = self.config["repositories"][repo_name]["repo"]
            results['subtree'] = self.config["repositories"][repo_name]["subtree"]
        except KeyError:
            raise ValueError("Missing repositories config for '%s'" % repo_name)
        else:
            return results
        
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--pack-to-expand",
                        help="Repo to expand",
                        default="st2contrib",
                        dest="repo")
    parser.add_argument("-a", "--action",
                        help="Run this script as an action",
                        action="store_true",
                        dest="action", default=True)
    args = parser.parse_args()

    pack_config_file = "../config.yaml"

    if os.path.exists(pack_config_file):
        f = open(pack_config_file)
        config = yaml.safe_load(f)
    else:
        config = None

    action = expand_repo_name(config)
    action_results = action.run(args.repo)

    print(json.dumps( action_results, sort_keys=True, indent=2))
