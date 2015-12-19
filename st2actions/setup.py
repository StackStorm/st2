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

import os.path

from setuptools import setup, find_packages

from dist_utils import fetch_requirements
from dist_utils import apply_vagrant_workaround
from st2actions import __version__

ST2_COMPONENT = 'st2actions'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, 'requirements.txt')

install_reqs, dep_links = fetch_requirements(REQUIREMENTS_FILE)

apply_vagrant_workaround()
setup(
    name=ST2_COMPONENT,
    version=__version__,
    description='{} component'.format(ST2_COMPONENT),
    author='StackStorm',
    author_email='info@stackstorm.com',
    install_requires=install_reqs,
    dependency_links=dep_links,
    test_suite=ST2_COMPONENT,
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['setuptools', 'tests']),
    scripts=[
        'bin/st2actionrunner',
        'bin/st2notifier',
        'bin/st2resultstracker',
        'bin/runners.sh'
    ],
    entry_points={
        'console_scripts': [
            'st2actionrunner = st2actions.cmd.actionrunner.main',
            'st2notifier = st2actions.cmd.st2notifier.main',
            'st2resultstracker = st2actions.cmd.st2resultstracker.main'
    ]
    },
    options={
          'build_scripts': {
              'executable': '/usr/share/python/st2actions/bin/python',
          },
    }
)
