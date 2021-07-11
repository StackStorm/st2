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

"""
Plugin which tells Pylint how to handle classes which define attributes using jsonschema
in "schema" class attribute.

Those classes dyamically assign attributes defined in the schema on the class inside the
constructor.
"""

import astroid
import six

from astroid import MANAGER
from astroid import nodes
from astroid import scoped_nodes

# A list of class names for which we want to skip the checks
CLASS_NAME_BLACKLIST = ["ExecutionSpecificationAPI"]


def register(linter):
    pass


def infer_copy_deepcopy(node):
    if not (
        isinstance(node.value, nodes.Call)
        and node.value.func.as_string() == "copy.deepcopy"
    ):
        return
    return node.value.args[0].infer()


def transform(cls):
    if cls.name in CLASS_NAME_BLACKLIST:
        return

    if cls.name.endswith("API") or "schema" in cls.locals:
        # This is a class which defines attributes in "schema" variable using json schema.
        # Those attributes are then assigned during run time inside the constructor
        schema_dict_node = next(cls.igetattr("schema"))

        extra_schema_properties = {}

        if schema_dict_node is astroid.Uninferable:
            # schema = copy.deepcopy(ActionAPI.schema)

            assigns = [n for n in cls.get_children() if isinstance(n, nodes.Assign)]
            schema_assign_name_node = cls.local_attr("schema")[0]
            schema_assign_node = next(
                assign
                for assign in assigns
                if assign.targets[0] == schema_assign_name_node
            )
            assigns.remove(schema_assign_node)

            # We only care about "schema = copy.deepcopy(...)"
            schema_dict_node = infer_copy_deepcopy(schema_assign_node)
            if not schema_dict_node:
                return

            for assign_node in assigns:
                # schema["properties"]["ttl"] = {...}
                target = assign_node.targets[0]
                property_name_node = None
                try:
                    if (
                        isinstance(target, nodes.Subscript)
                        and target.value.value.name == "schema"
                        and target.value.slice.value.value == "properties"
                    ):
                        propery_name_node = target.slice.value
                    else:
                        # not schema["properties"]
                        continue
                except AttributeError:
                    continue

                # schema["properties"]["execution"] = copy.deepcopy(ActionExecutionAPI.schema)
                inferred_value = infer_copy_deepcopy(assign_node.value)

                extra_schema_properties[property_name_node] = (
                    inferred_value if inferred_value else assign_node.value
                )

        if not isinstance(schema_dict_node, nodes.Dict):
            # Not a class we are interested in (like BaseAPI)
            return

        properties_dict_node = None
        for key_node, value_node in schema_dict_node.items:
            if key_node.value == "properties":
                properties_dict_node = value_node
                break

        if not properties_dict_node and not extra_schema_properties:
            # Not a class we can do anything with
            return

        for property_name_node, property_data_node in properties_dict_node.items + list(
            extra_schema_properties.items()
        ):
            property_name = property_name_node.value.replace(
                "-", "_"
            )  # Note: We do the same in Python code

            property_type_node = None
            for property_key_node, property_value_node in property_data_node.items:
                if property_key_node.value == "type":
                    property_type_node = property_value_node
                    break
            if property_type_node and not isinstance(property_type_node, nodes.Dict):
                # if infer_copy_deepcopy already ran, and now we need to resolve the dict
                property_type_node = next(property_type_node.infer())

                # an indirect reference to copy.deepcopy() as in:
                #   REQUIRED_ATTR_SCHEMAS = {"action": copy.deepcopy(ActionAPI.schema)}
                #   schema = {"properties": {"action": REQUIRED_ATTR_SCHEMAS["action"]}}
                node = infer_copy_deepcopy(property_type_node)

                if node:
                    property_type_node = node

            property_type = property_type_node.value if property_type_node else None

            if isinstance(property_type, (list, tuple)):
                # Hack for attributes with multiple types (e.g. string, null)
                property_type = property_type[0]

            if property_type == "object":
                node = nodes.Dict()
            elif property_type == "array":
                node = nodes.List()
            elif property_type == "integer":
                node = scoped_nodes.builtin_lookup("int")[1][0]
            elif property_type == "number":
                node = scoped_nodes.builtin_lookup("float")[1][0]
            elif property_type == "string":
                node = scoped_nodes.builtin_lookup("str")[1][0]
            elif property_type == "boolean":
                node = scoped_nodes.builtin_lookup("bool")[1][0]
            elif property_type == "null":
                node = scoped_nodes.builtin_lookup("None")[1][0]
            else:
                # Unknown type
                node = astroid.ClassDef(property_name, None)

            cls.locals[property_name] = [node]


MANAGER.register_transform(astroid.ClassDef, transform)
