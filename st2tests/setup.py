# -*- coding: utf-8 -*-
# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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

from setuptools import setup, find_packages

from dist_utils import fetch_requirements
from dist_utils import apply_vagrant_workaround
from dist_utils import get_version_string

ST2_COMPONENT = "st2tests"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, "requirements.txt")
INIT_FILE = os.path.join(BASE_DIR, "st2tests/__init__.py")


install_reqs, dep_links = fetch_requirements(REQUIREMENTS_FILE)

# Note: we can't directly import __version__ from __init__ because of aliased imports in init
# which would result in setup.py requiring eventlet and other dependencies to run.


apply_vagrant_workaround()
setup(
    name=ST2_COMPONENT,
    version=get_version_string(INIT_FILE),
    description="{} StackStorm event-driven automation platform component".format(
        ST2_COMPONENT
    ),
    author="StackStorm",
    author_email="info@stackstorm.com",
    license="Apache License (2.0)",
    url="https://stackstorm.com/",
    install_requires=install_reqs,
    dependency_links=dep_links,
    test_suite=ST2_COMPONENT,
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=["setuptools", "tests"]),
)
