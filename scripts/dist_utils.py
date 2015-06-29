# -*- coding: utf-8 -*-
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

from pip.req import parse_requirements

__all__ = [
    'fetch_requirements'
]


def fetch_requirements(requirements_file_path):
    """
    Return a list of requirements and links by parsing the provided requirements file.
    """
    links = []
    reqs = []
    for req in parse_requirements(requirements_file_path, session=False):
        if req.link:
            links.append(str(req.link))
        reqs.append(str(req.req))
    return (reqs, links)


def parse_version(version_file_path):
    """
    Parse a version string from the provided version file.
    """
    # TODO: For backward compatibility we use a global version file but eventually we should
    # support per component versioning
    with open(version_file_path, 'r') as f:
        version = f.read().strip()

    return version
