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

import glob

from st2common.content.loader import MetaLoader
from st2common.content.loader import ContentPackLoader

__all__ = [
    'ResourceRegistrar'
]


class ResourceRegistrar(object):
    ALLOWED_EXTENSIONS = []

    def __init__(self):
        self._meta_loader = MetaLoader()
        self._pack_loader = ContentPackLoader()

    def get_resources_from_pack(self, resources_dir):
        resources = []
        for ext in self.ALLOWED_EXTENSIONS:
            resources_glob = resources_dir

            if resources_dir.endswith('/'):
                resources_glob = resources_dir + ext
            else:
                resources_glob = resources_dir + '/*' + ext

            resource_files = glob.glob(resources_glob)
            resources.extend(resource_files)

        resources = sorted(resources)
        return resources
