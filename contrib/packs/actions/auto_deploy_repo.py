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

class Auto_Deploy_Repo(Action):
    def __init__(self, config=None):
        super(Auto_Deploy_Repo, self).__init__(config=config)

    def run(self, branch, repo_name):
        results = {}

        try:
            results['deployment_branch'] = self.config["repositories"][repo_name]["auto_deployment"]["branch"]
            results['notify_channel'] = self.config["repositories"][repo_name]["auto_deployment"]["notify_channel"]
        except KeyError:
            raise ValueError("No repositories or auto_deployment config for '%s'" % repo_name)
        else:
            if branch == "refs/heads/%s" % results['deployment_branch']:
                return results
            else:
                raise ValueError("Branch %s for %s should not be auto deployed" % (branch, repo_name))
        
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--repo-name",
                        help="Repository name to look up",
                        default="st2contrib",
                        dest="repo_name")
    args = parser.parse_args()

    pack_config_file = "../config.yaml"

    if os.path.exists(pack_config_file):
        f = open(pack_config_file)
        config = yaml.safe_load(f)
    else:
        config = None

    action = Auto_Deploy_Repo(config)
    action_results = action.run(branch="refs/heads/master",
                                repo_name=args.repo_name)

    print(json.dumps( action_results, sort_keys=True, indent=2))
