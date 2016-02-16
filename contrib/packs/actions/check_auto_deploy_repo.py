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

class CheckAutoDeployRepo(Action):
    def run(self, branch, repo_name):
        """Returns the required data to complete an auto deployment of a pack in repo_name.

        The branch is expected to be in the format _refs/heads/foo_, if
        it's not then the comprassion will fail.

        Returns: A Dict with deployment_branch and notify_channel.

        Raises:
          ValueError: If the repo_name should not be auto deployed or
                      config is not complete.
        """
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
