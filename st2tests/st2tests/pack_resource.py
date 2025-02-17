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
import inspect

from unittest import TestCase

__all__ = ["BasePackResourceTestCase"]


class BasePackResourceTestCase(TestCase):
    """
    Base test class for all the pack resource test classes.

    Contains some utility methods for loading fixtures from disk, etc.
    """

    def get_fixture_content(self, fixture_path):
        """
        Return raw fixture content for the provided fixture path.

        :param fixture_path: Fixture path relative to the tests/fixtures/ directory.
        :type fixture_path: ``str``
        """
        base_pack_path = self._get_base_pack_path()
        fixtures_path = os.path.join(base_pack_path, "tests/fixtures/")
        fixture_path = os.path.join(fixtures_path, fixture_path)

        with open(fixture_path, "r") as fp:
            content = fp.read()

        return content

    def _get_base_pack_path(self):
        test_file_path = inspect.getfile(self.__class__)
        base_pack_path = os.path.join(os.path.dirname(test_file_path), "..")
        base_pack_path = os.path.abspath(base_pack_path)
        return base_pack_path
