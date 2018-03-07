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

from __future__ import absolute_import
import os.path

from setuptools import setup
from setuptools import find_packages

from dist_utils import fetch_requirements
from dist_utils import apply_vagrant_workaround

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, 'requirements.txt')

install_reqs, dep_links = fetch_requirements(REQUIREMENTS_FILE)

apply_vagrant_workaround()
setup(
    name='stackstorm-runner-orchestra',
    version='2.5.0',
    description='Orchestra workflow runner for StackStorm event-driven automation platform',
    author='StackStorm',
    author_email='info@stackstorm.com',
    license='Apache License (2.0)',
    url='https://stackstorm.com/',
    install_requires=install_reqs,
    dependency_links=dep_links,
    test_suite='tests',
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['setuptools', 'tests']),
    package_data={'orchestra': ['runner.yaml']},
    scripts=[],
    entry_points={
        'st2common.runners.runner': [
            'orchestra = orchestra.orchestra',
        ],
    }
)
