#!/usr/bin/env python2.7
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

# Note: We should re-enable usage of dist_utils once we ensure
# that we install new version of virtualenv which ships with
# pip >= 6.1 in all the environments
# from dist_utils import fetch_requirements
# from dist_utils import apply_vagrant_workaround
from st2client import __version__

ST2_COMPONENT = 'st2client'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, 'requirements.txt')

# install_reqs, dep_links = fetch_requirements(REQUIREMENTS_FILE)
# apply_vagrant_workaround()

setup(
    name=ST2_COMPONENT,
    version=__version__,
    description=('Python client library and CLI for the StackStorm (st2) event-driven '
                 'automation platform.'),
    author='StackStorm',
    author_email='info@stackstorm.com',
    license='Apache License (2.0)',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7'
    ],
    install_requires=[
        'jsonpath-rw>=1.3.0',
        'prettytable',
        'python-dateutil',
        'pyyaml<4.0,>=3.11',
        'requests<3.0,>=2.7.0',
        'six==1.10.0'
    ],
    dependency_links=[],
    test_suite=ST2_COMPONENT,
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['setuptools', 'tests']),
    entry_points={
        'console_scripts': [
            'st2 = st2client.shell:main'
        ]
    }
)
