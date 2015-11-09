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

"""
Plugin which tells Pylint how to handle classes which define attributes using jsonschema
in "schema" class attribute.

Those classes dyamically assign attributes defined in the schema on the class inside the
constructor.
"""

from astroid import MANAGER
from astroid import scoped_nodes


def register(linter):
    pass


def transform(cls):
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

        properties = schema.get('properties', {}).keys()

        for property_name in properties:
            property_name = property_name.replace('-', '_')  # Note: We do the same in Python code
            cls.locals[property_name] = [scoped_nodes.Class(property_name, None)]


MANAGER.register_transform(scoped_nodes.Class, transform)
