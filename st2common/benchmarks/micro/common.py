# Copyright 2021 The StackStorm Authors.
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

import os

import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.abspath(os.path.join(BASE_DIR, "../fixtures/json"))


PYTEST_FIXTURE_FILE_PARAM_NO_8MB_DECORATOR = pytest.mark.parametrize(
    "fixture_file",
    [
        "tiny_1.json",
        "json_61kb.json",
        "json_647kb.json",
        "json_4mb.json",
        "json_4mb_single_large_field.json",
    ],
    ids=[
        "tiny_1",
        "json_61kb",
        "json_647kb",
        "json_4mb",
        "json_4mb_single_large_field",
    ],
)

# NOTE: On CI we skip 8 MB fixture file since it's very slow and substantially slows down that
# workflow.
ST2_CI = os.environ.get("ST2_CI", "false").lower() == "true"

if ST2_CI:
    PYTEST_FIXTURE_FILE_PARAM_DECORATOR = PYTEST_FIXTURE_FILE_PARAM_NO_8MB_DECORATOR
else:
    PYTEST_FIXTURE_FILE_PARAM_DECORATOR = pytest.mark.parametrize(
        "fixture_file",
        [
            "tiny_1.json",
            "json_61kb.json",
            "json_647kb.json",
            "json_4mb.json",
            "json_8mb.json",
            "json_4mb_single_large_field.json",
        ],
        ids=[
            "tiny_1",
            "json_61kb",
            "json_647kb",
            "json_4mb",
            "json_8mb",
            "json_4mb_single_large_field",
        ],
    )
