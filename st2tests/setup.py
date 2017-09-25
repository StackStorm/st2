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

import re
import os.path

from setuptools import setup, find_packages

from dist_utils import fetch_requirements
from dist_utils import apply_vagrant_workaround

ST2_COMPONENT = 'st2tests'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, 'requirements.txt')
INIT_FILE = os.path.join(BASE_DIR, 'st2tests/__init__.py')


install_reqs, dep_links = fetch_requirements(REQUIREMENTS_FILE)

# Note: we can't directly import __version__ from __init__ because of aliased imports in init
# which would result in setup.py requiring eventlet and other dependencies to run.


def get_version_string():
    with open(INIT_FILE, 'r') as fp:
        content = fp.read()
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                                  content, re.M)
        if version_match:
            return version_match.group(1)

        raise RuntimeError('Unable to find version string.')


apply_vagrant_workaround()
setup(
    name=ST2_COMPONENT,
    version=get_version_string(),
    description='{}'.format(ST2_COMPONENT),
    author='StackStorm',
    author_email='info@stackstorm.com',
    install_requires=install_reqs,
    dependency_links=dep_links,
    test_suite=ST2_COMPONENT,
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['setuptools', 'tests'])
)
