# Copyright 2020 The StackStorm Authors.
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

import unittest
import yaml

from st2common.util import spec_loader

# indicate to pants that this test uses this fixture.
from st2tests.fixtures.specs import __package__ as specs_fixture_package


class SpecLoaderTest(unittest.TestCase):
    def test_spec_loader(self):
        self.assertTrue(
            isinstance(spec_loader.load_spec("st2common", "openapi.yaml.j2"), dict)
        )

    def test_bad_spec_duplicate_keys(self):
        self.assertRaisesRegex(
            yaml.constructor.ConstructorError,
            'found duplicate key "swagger"',
            spec_loader.load_spec,
            specs_fixture_package,
            "openapi.yaml.j2",
        )
