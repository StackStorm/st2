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

from orquesta_runner import __version__

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, "requirements.txt")

install_reqs, dep_links = fetch_requirements(REQUIREMENTS_FILE)

apply_vagrant_workaround()
setup(
    name="stackstorm-runner-orquesta",
    version=__version__,
    description="Orquesta workflow runner for StackStorm event-driven automation platform",
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
    package_data={"orquesta_runner": ["runner.yaml"]},
    scripts=[],
    entry_points={
        "st2common.runners.runner": [
            "orquesta = orquesta_runner.orquesta_runner",
        ],
        "orquesta.expressions.functions": [
            "st2kv = orquesta_functions.st2kv:st2kv_",
            "task = orquesta_functions.runtime:task",
            "basename = st2common.expressions.functions.path:basename",
            "dirname = st2common.expressions.functions.path:dirname",
            "from_json_string = st2common.expressions.functions.data:from_json_string",
            "from_yaml_string = st2common.expressions.functions.data:from_yaml_string",
            "json_dump = st2common.expressions.functions.data:to_json_string",
            "json_parse = st2common.expressions.functions.data:from_json_string",
            "json_escape = st2common.expressions.functions.data:json_escape",
            "jsonpath_query = st2common.expressions.functions.data:jsonpath_query",
            "regex_match = st2common.expressions.functions.regex:regex_match",
            "regex_replace = st2common.expressions.functions.regex:regex_replace",
            "regex_search = st2common.expressions.functions.regex:regex_search",
            "regex_substring = st2common.expressions.functions.regex:regex_substring",
            (
                "to_human_time_from_seconds = "
                "st2common.expressions.functions.time:to_human_time_from_seconds"
            ),
            "to_json_string = st2common.expressions.functions.data:to_json_string",
            "to_yaml_string = st2common.expressions.functions.data:to_yaml_string",
            "use_none = st2common.expressions.functions.data:use_none",
            "version_compare = st2common.expressions.functions.version:version_compare",
            "version_more_than = st2common.expressions.functions.version:version_more_than",
            "version_less_than = st2common.expressions.functions.version:version_less_than",
            "version_equal = st2common.expressions.functions.version:version_equal",
            "version_match = st2common.expressions.functions.version:version_match",
            "version_bump_major = st2common.expressions.functions.version:version_bump_major",
            "version_bump_minor = st2common.expressions.functions.version:version_bump_minor",
            "version_bump_patch = st2common.expressions.functions.version:version_bump_patch",
            "version_strip_patch = st2common.expressions.functions.version:version_strip_patch",
            "yaml_dump = st2common.expressions.functions.data:to_yaml_string",
            "yaml_parse = st2common.expressions.functions.data:from_yaml_string",
        ],
    },
)
