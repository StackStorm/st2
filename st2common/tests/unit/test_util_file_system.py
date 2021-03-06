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
import os
import os.path

import unittest2

from st2common.util.file_system import get_file_list

CURRENT_DIR = os.path.dirname(__file__)
ST2TESTS_DIR = os.path.join(CURRENT_DIR, "../../../st2tests/st2tests")


class FileSystemUtilsTestCase(unittest2.TestCase):
    def test_get_file_list(self):
        # Standard exclude pattern
        directory = os.path.join(ST2TESTS_DIR, "policies")
        expected = [
            "mock_exception.py",
            "concurrency.py",
            "__init__.py",
            "meta/mock_exception.yaml",
            "meta/concurrency.yaml",
            "meta/__init__.py",
        ]
        result = get_file_list(directory=directory, exclude_patterns=["*.pyc"])
        self.assertItemsEqual(expected, result)

        # Custom exclude pattern
        expected = [
            "mock_exception.py",
            "concurrency.py",
            "__init__.py",
            "meta/__init__.py",
        ]
        result = get_file_list(
            directory=directory, exclude_patterns=["*.pyc", "*.yaml"]
        )
        self.assertItemsEqual(expected, result)
