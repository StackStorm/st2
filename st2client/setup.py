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

from pip.req import parse_requirements
from setuptools import setup, find_packages

from st2client import __version__

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ST2_COMPONENT = os.path.basename(BASE_DIR)
REQUIREMENTS_FILE = os.path.join(BASE_DIR, 'requirements.txt')


def fetch_requirements():
    links = []
    reqs = []
    for req in parse_requirements(REQUIREMENTS_FILE, session=False):
        if req.link:
            links.append(str(req.link))
        reqs.append(str(req.req))
    return (reqs, links)

install_reqs, dep_links = fetch_requirements()


setup(
    name=ST2_COMPONENT,
    version=__version__,
    description='CLI and python client library for the StackStorm (st2) automation platform.',
    author='StackStorm',
    author_email='info@stackstorm.com',
    license='Apache License (2.0)',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7'
    ],
    install_requires=install_reqs,
    dependency_links=dep_links,
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
