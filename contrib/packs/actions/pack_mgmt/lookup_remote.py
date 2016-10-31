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

import yaml

from st2common.runners.base_action import Action
from st2common.services.packs import get_pack_from_index

MANIFEST_FILE = 'pack.yaml'


class LookupRemote(Action):
    def run(self, pack):
        index_pack = get_pack_from_index(pack)
        return {
            'pack': index_pack,
            # Would be nice to fetch the original pack.yaml from the index repo,
            # but then we would lose support for user-created indexes.
            'pack_formatted': yaml.dump(index_pack) if index_pack else None
        }
