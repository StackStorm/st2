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

from __future__ import absolute_import
import pkg_resources

import jinja2
import yaml

from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import st2common.constants.pack
import st2common.constants.action

from st2common.rbac.types import PermissionType
from st2common.util import isotime

__all__ = [
    'load_spec',
    'generate_spec'
]

ARGUMENTS = {
    'DEFAULT_PACK_NAME': st2common.constants.pack.DEFAULT_PACK_NAME,
    'LIVEACTION_STATUSES': st2common.constants.action.LIVEACTION_STATUSES,
    'PERMISSION_TYPE': PermissionType,
    'ISO8601_UTC_REGEX': isotime.ISO8601_UTC_REGEX
}


class UniqueKeyLoader(Loader):
    """
    YAML loader which throws on a duplicate key.
    """
    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise ConstructorError("while constructing a mapping", node.start_mark,
                       "found unacceptable key (%s)" % exc, key_node.start_mark)
            # check for duplicate keys
            if key in mapping:
                raise ConstructorError("while constructing a mapping", node.start_mark,
                       "found duplicate key", key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping


def load_spec(module_name, spec_file, allow_duplicate_keys=False):
    spec_string = generate_spec(module_name, spec_file)

    # 1. Check for duplicate keys
    if not allow_duplicate_keys:
        yaml.load(spec_string, UniqueKeyLoader)

    # 2. Generate actual spec
    spec = yaml.safe_load(spec_string)
    return spec


def generate_spec(module_name, spec_file):
    spec_template = pkg_resources.resource_string(module_name, spec_file)
    if not isinstance(spec_template, str):
        spec_template = spec_template.decode()
    spec_string = jinja2.Template(spec_template).render(**ARGUMENTS)

    return spec_string
