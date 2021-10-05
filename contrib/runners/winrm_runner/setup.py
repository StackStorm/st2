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

from setuptools import setup
from setuptools import find_packages

from dist_utils import fetch_requirements
from dist_utils import apply_vagrant_workaround

from winrm_runner import __version__

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, "requirements.txt")

install_reqs, dep_links = fetch_requirements(REQUIREMENTS_FILE)

apply_vagrant_workaround()
setup(
    name="stackstorm-runner-winrm",
    version=__version__,
    description=(
        "WinRM shell command and PowerShell script action runner for"
        " the StackStorm event-driven automation platform"
    ),
    author="StackStorm",
    author_email="info@stackstorm.com",
    license="Apache License (2.0)",
    url="https://stackstorm.com/",
    install_requires=install_reqs,
    dependency_links=dep_links,
    test_suite="tests",
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=["setuptools", "tests"]),
    package_data={"winrm_runner": ["runner.yaml"]},
    scripts=[],
    entry_points={
        "st2common.runners.runner": [
            "winrm-cmd = winrm_runner.winrm_command_runner",
            "winrm-ps-cmd = winrm_runner.winrm_ps_command_runner",
            "winrm-ps-script = winrm_runner.winrm_ps_script_runner",
        ],
    },
)
