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


def infer_copy_deepcopy(call_node):
    if not (
        isinstance(call_node, nodes.Call)
        and call_node.func.as_string() == "copy.deepcopy"
    ):
        return
    return next(call_node.args[0].infer())


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
            schema_dict_node = infer_copy_deepcopy(schema_assign_node.value)
            if not schema_dict_node:
                return

            for assign_node in assigns:
                # schema["properties"]["ttl"] = {...}
                target = assign_node.targets[0]
                try:
                    if (
                        isinstance(target, nodes.Subscript)
                        and target.value.value.name == "schema"
                        and target.value.slice.value.value == "properties"
                    ):
                        property_name_node = target.slice.value
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

            # an indirect reference to copy.deepcopy() as in:
            #   REQUIRED_ATTR_SCHEMAS = {"action": copy.deepcopy(ActionAPI.schema)}
            #   schema = {"properties": {"action": REQUIRED_ATTR_SCHEMAS["action"]}}
            if isinstance(property_data_node, nodes.Subscript):
                var_name = property_data_node.value.name
                subscript = property_data_node.slice.value.value

                # lookup var by name (assume its at module level)
                var_node = next(cls.root().igetattr(var_name))

                # assume it is a dict at this point
                data_node = None
                for key_node, value_node in var_node.items:
                    if key_node.value == subscript:
                        # infer will resolve a Dict
                        data_node = next(value_node.infer())
                        if data_node is astroid.Uninferable:
                            data_node = infer_copy_deepcopy(value_node)
                        break
                if data_node:
                    property_data_node = data_node

            if not isinstance(property_data_node, nodes.Dict):
                # if infer_copy_deepcopy already ran, we may need to resolve the dict
                data_node = next(property_data_node.infer())
                if data_node is not astroid.Uninferable:
                    property_data_node = data_node

            property_type_node = None
            if isinstance(property_data_node, nodes.Dict):
                for property_key_node, property_value_node in property_data_node.items:
                    if property_key_node.value == "type":
                        property_type_node = next(property_value_node.infer())
                        break

            if property_type_node is None and isinstance(
                property_data_node, nodes.Attribute
            ):
                # reference schema from another file
                #   from ... import TriggerAPI
                #   schema = {"properties": {"trigger": TriggerAPI.schema}}
                property_type = "object"
            elif property_type_node is None:
                property_type = None
            elif isinstance(property_type_node, nodes.Const):
                property_type = property_type_node.value
            elif isinstance(property_type_node, (nodes.List, nodes.Tuple)):
                # Hack for attributes with multiple types (e.g. string, null)
                property_type = property_type_node.elts[
                    0
                ].value  # elts has "elements" in the list/tuple
            else:
                raise Exception(property_type_node.repr_tree())

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
