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

class Packs_Check_Pack_Auto_Deploy(Action):
    def __init__(self, config=None):
        super(Packs_Check_Pack_Auto_Deploy, self).__init__(config=config)

    def run(self, branch, repository):
        exit_code = 1

        # Set up the results
        results = {}
        results['notify_channel'] = None
        results['deployment_branch'] = None

        if self.config.has_key("repositories"):
            if self.config["repositories"].has_key(repository):
                if self.config["repositories"][repository].has_key("auto_deployment"):
                    auto_deploy_branch = self.config["repositories"][repository]["auto_deployment"]["branch"]
                    results['notify_channel'] = self.config["repositories"][repository]["auto_deployment"]["notify_channel"]

                    if branch == "refs/heads/%s" % auto_deploy_branch:
                        results['deployment_branch'] = auto_deploy_branch
                        exit_code = 0
                    else:
                        self.logger.error("Branch %s for %s should be auto deployed" % (auto_deplog_branch,
                                                                                        repository) )
                        exit_code = 1
                else:
                    self.logger.error("Branch %s for %s does not have auto_dep_branch set" % (branch,
                                                                                              repository) )
        else:
            self.logger.error("Unknown repository: %s", repository)
            exit_code = 1
        
        if exit_code == 0:
            return results
        else:
            print json.dumps(results, sort_keys=True)


        sys.exit(exit_code)
        
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--repository",
                        help="Repository to look up",
                        default="st2contrib",
                        dest="repo")
    args = parser.parse_args()

    pack_config_file = "../config.yaml"

    if os.path.exists(pack_config_file):
        f = open(pack_config_file)
        config = yaml.safe_load(f)
    else:
        config = None

    action = Packs_Check_Pack_Auto_Deploy(config)
    action_results = action.run(branch="refs/heads/master",
                                repository=args.repo)

    print(json.dumps( action_results, sort_keys=True, indent=2))
