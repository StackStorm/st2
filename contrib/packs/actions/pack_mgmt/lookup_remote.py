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

import re

import yaml
import requests

from st2common.runners.base_action import Action
from st2common.services.packs import get_pack_from_index

MANIFEST_FILE = 'pack.yaml'
EXCHANGE_REPO_URL_REGEX = r'(git@|https?://)github\.com[/:]StackStorm-Exchange/stackstorm-\S+'
EXCHANGE_YAML_PATH = 'https://index.stackstorm.org/v1/packs/%s.yaml'


class LookupRemote(Action):
    """Get detailed information about an available pack from the pack index"""
    def run(self, pack):
        pack_meta = get_pack_from_index(pack)
        pack_formatted = None
        # Try to get the original yaml file because we know
        # how it's stored in the Exchange, otherwise fall back
        # to transforming json.
        if pack_meta:
            if re.match(EXCHANGE_REPO_URL_REGEX, pack_meta['repo_url'], re.IGNORECASE):
                pack_formatted = requests.get(EXCHANGE_YAML_PATH % pack).text
            else:
                pack_formatted = yaml.dump(pack_meta)

        return {
            'pack': pack_meta,
            'pack_formatted': pack_formatted
        }
