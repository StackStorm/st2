#!/usr/bin/env python
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

import os.path

from setuptools import setup, find_packages

from dist_utils import fetch_requirements
from dist_utils import apply_vagrant_workaround

from st2client import __version__

ST2_COMPONENT = "st2client"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, "requirements.txt")
README_FILE = os.path.join(BASE_DIR, "README.rst")

install_reqs, dep_links = fetch_requirements(REQUIREMENTS_FILE)
apply_vagrant_workaround()

with open(README_FILE) as f:
    readme = f.read()

setup(
    name=ST2_COMPONENT,
    version=__version__,
    description=(
        "Python client library and CLI for the StackStorm (st2) event-driven "
        "automation platform."
    ),
    long_description=readme,
    long_description_content_type="text/x-rst",
    author="StackStorm",
    author_email="info@stackstorm.com",
    url="https://stackstorm.com/",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    install_requires=install_reqs,
    dependency_links=dep_links,
    test_suite=ST2_COMPONENT,
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=["setuptools", "tests"]),
    entry_points={"console_scripts": ["st2 = st2client.shell:main"]},
    project_urls={
        "Pack Exchange": "https://exchange.stackstorm.org",
        "Repository": "https://github.com/StackStorm/st2",
        "Documentation": "https://docs.stackstorm.com",
        "Community": "https://stackstorm.com/community-signup",
        "Questions": "https://github.com/StackStorm/st2/discussions",
        "Donate": "https://funding.communitybridge.org/projects/stackstorm",
        "News/Blog": "https://stackstorm.com/blog",
        "Security": "https://docs.stackstorm.com/latest/security.html",
        "Bug Reports": "https://github.com/StackStorm/st2/issues",
    },
)
