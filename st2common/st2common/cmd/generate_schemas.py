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

"""
A script that generates st2 metadata (pack, action, rule, ...) schemas.
This is used by `st2-generate-schemas` to update contrib/schemas/*.json.
"""

from __future__ import absolute_import

import json
import os
import sys

from st2common.models.api import action as action_models
from st2common.models.api import pack as pack_models
from st2common.models.api import policy as policy_models
from st2common.models.api import rule as rule_models
from st2common.models.api import sensor as sensor_models

__all__ = ["generate_schemas", "write_schemas"]

content_models = {
    "pack": pack_models.PackAPI,
    "action": action_models.ActionAPI,
    "alias": action_models.ActionAliasAPI,
    "policy": policy_models.PolicyAPI,
    "rule": rule_models.RuleAPI,
    "sensor": sensor_models.SensorTypeAPI,
}


default_schemas_dir = "."


def generate_schemas():
    for name, model in content_models.items():
        schema_text = json.dumps(model.schema, indent=4)

        yield name, schema_text


def write_schemas(schemas_dir):
    for name, schema_text in generate_schemas():
        print('Generated schema for the "%s" model.' % name)

        schema_file = os.path.join(schemas_dir, name + ".json")
        print('Schema will be written to "%s".' % schema_file)

        with open(schema_file, "w") as f:
            f.write(schema_text)
            f.write("\n")


def main():
    argv = sys.argv[1:]

    # 1st positional parameter is the destination directory
    schemas_dir = argv[0] if argv else default_schemas_dir

    write_schemas(schemas_dir)

    return 0
