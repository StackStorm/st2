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

from __future__ import absolute_import

import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

from yaml import constructor
from yaml import nodes


# Custom YAML loader that throw an exception on duplicate key.
# Credit: https://gist.github.com/pypt/94d747fe5180851196eb
class UniqueKeyLoader(SafeLoader):
    def construct_mapping(self, node, deep=False):
        if not isinstance(node, nodes.MappingNode):
            raise constructor.ConstructorError(
                None,
                None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark,
            )
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found unacceptable key (%s)" % exc,
                    key_node.start_mark,
                )
            # check for duplicate keys
            if key in mapping:
                raise constructor.ConstructorError(
                    'found duplicate key "%s"' % key_node.value
                )
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping


# Add UniqueKeyLoader to the yaml SafeLoader so it is invoked by safe_load.
yaml.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    UniqueKeyLoader.construct_mapping,
    Loader=SafeLoader,
)


def unique_key_loader_safe_load(text):
    # The use of yaml.load and passing SafeLoader is the same as yaml.safe_load which
    # makes the same call. The difference here is that we use CSafeLoader where possible
    # to improve performance and yaml.safe_load uses the python implementation by default.
    return yaml.load(text, SafeLoader)
