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
Plugin which tells Pylint how to handle classes which define attributes using jsonschema
in "schema" class attribute.

Those classes dyamically assign attributes defined in the schema on the class inside the
constructor.
"""

import six

from astroid import MANAGER
from astroid import nodes
from astroid import scoped_nodes

# A list of class names for which we want to skip the checks
CLASS_NAME_BLACKLIST = [
    'ExecutionSpecificationAPI'
]


def register(linter):
    pass


def transform(cls):
    if cls.name in CLASS_NAME_BLACKLIST:
        return

    if cls.name.endswith('API') or 'schema' in cls.locals:
        # This is a class which defines attributes in "schema" variable using json schema.
        # Those attributes are then assigned during run time inside the constructor
        fqdn = cls.qname()
        module_name, class_name = fqdn.rsplit('.', 1)

        module = __import__(module_name, fromlist=[class_name])
        actual_cls = getattr(module, class_name)

        schema = actual_cls.schema

        if not isinstance(schema, dict):
            # Not a class we are interested in
            return

        properties = schema.get('properties', {})
        for property_name, property_data in six.iteritems(properties):
            property_name = property_name.replace('-', '_')  # Note: We do the same in Python code
            property_type = property_data.get('type', None)

            if isinstance(property_type, (list, tuple)):
                # Hack for attributes with multiple types (e.g. string, null)
                property_type = property_type[0]

            if property_type == 'object':
                node = nodes.Dict()
            elif property_type == 'array':
                node = nodes.List()
            elif property_type == 'integer':
                node = scoped_nodes.builtin_lookup('int')[1][0]
            elif property_type == 'number':
                node = scoped_nodes.builtin_lookup('float')[1][0]
            elif property_type == 'string':
                node = scoped_nodes.builtin_lookup('str')[1][0]
            elif property_type == 'boolean':
                node = scoped_nodes.builtin_lookup('bool')[1][0]
            elif property_type == 'null':
                node = scoped_nodes.builtin_lookup('None')[1][0]
            else:
                # Unknown type
                node = scoped_nodes.Class(property_name, None)

            cls.locals[property_name] = [node]


MANAGER.register_transform(scoped_nodes.Class, transform)
