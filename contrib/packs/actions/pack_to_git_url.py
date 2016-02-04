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

debug = False

class Packs_pack_to_git_url(Action):
    def __init__(self, config=None):
        super(Packs_pack_to_git_url, self).__init__(config=config)

    def expand_repo_details(self, pack_to_expand, item):
        if self.config["repositories"][pack_to_expand].has_key(item):
            return self.config["repositories"][pack_to_expand][item]
        else:
            if self.config["repositories"]["default"].has_key(item):
                return self.config["repositories"]["default"][item]
            else:
                return None

    def run(self, pack_to_expand):
        exit_code = 0

        # Set up the results object
        results = {}
        results['pack_to_expand'] = pack_to_expand

        if pack_to_expand.count('/') == 0:
            results['pack'] = pack_to_expand
        elif pack_to_expand.count('/') == 1:
            (pack_to_expand, results['pack']) = pack_to_expand.split('/')
        elif pack_to_expand.count('/') == 2:
            (expand_user, expand_pack, results['pack']) = pack_to_expand.split('/')
            pack_to_expand = expand_user + '/' + expand_pack
        else:
            exit_code = 1
            self.logger.error("Too many /'s")

        if self.config.has_key("repositories"):
            if self.config["repositories"].has_key(pack_to_expand):
                user     = self.expand_repo_details(pack_to_expand, "user")
                port     = self.expand_repo_details(pack_to_expand, "port")
                protocol = self.expand_repo_details(pack_to_expand, "protocol")
                server   = self.expand_repo_details(pack_to_expand, "server")
                repo     = self.expand_repo_details(pack_to_expand, "repo")
                
                results['subtree'] = self.expand_repo_details(pack_to_expand, "subtree")

                if protocol == "ssh":
                    protocol = "ssh://git@"
                elif protocol == "https":
                    protocol = "https://"
                elif protocol == "http":
                    protocol = "http://"
                elif protocol == "git":
                    protocol = "git://"
                else:
                    exit_code = 1
                    self.logger.error("Invalid protocol!")
            else:
                exit_code = 1
                self.logger.error("Could not get Project Key for the Repo!")
        else:
            exit_code = 1
            self.logger.error("No config supplied!")

        if exit_code == 0:
            if port is not None:
                results['url'] = protocol + server + ":" + port + "/" + user + "/" + repo + ".git"
            else:
                results['url'] = protocol + server + "/" + user + "/" + repo + ".git"

            # Turn the results, 
            return results
            
        # exit with 1, if there is issues.
        sys.exit(exit_code)
        
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

    action = Packs_pack_to_git_url(config)
    action_results = action.run(args.repo)

    print(json.dumps( action_results, sort_keys=True, indent=2))
