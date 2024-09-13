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

Pylint uses static analysis on the python files it lints. This means that it does not
import any of the code using standard python libraries. Instead, it parses them into an
AST using the astroid library. Thus, it is safe to run Pylint on code that would
have import time side-effects without triggering those effects. When parsing a single file,
Pylint can parse the direct dependencies of that file without following the entire
import chain, which might include significant transient dependencies in 3rd party libraries.

Since pylint is using an AST instead of importing the code, it cannot know about the dynamic
attributes that get added to our API model classes. Plus, the schema itself is often
constructed by including copies of common sub schemas. So, the attributes are dynamic AND
the schemas that define those attributes are also dynamic.

So, in this plugin we have to do a bit of work to:

  1) extract the "schema =" assignment,
  2) parse the assigned value to find any other variables used in the schema object,
  3) extract the assignments for those other variables, and
  4) construct a final dictionary AST node that includes all the attributes that
     Pylint needs to know about on our model classes.

At this point, we have the schema, so then we:

  5) iterate over the schema properties,
  6) parse each property's value to find any other referenced variables,
  7) extract the assignments for those referenced variables,
  8) inspect the types of those properties (str, int, list, etc), and
  9) add new attribute AST nodes (of the appropriate type) to the class AST node.

Now, we return because Pylint can finally understand our API model objects without
importing them.
"""
# pylint: disable=E1120,E1125

import astroid

from astroid import MANAGER
from astroid import nodes
from astroid import scoped_nodes

# A list of class names for which we want to skip the checks
CLASS_NAME_SKIPLIST = ["ExecutionSpecificationAPI"]


def register(linter):
    pass


def infer_copy_deepcopy(call_node):
    """
    Look for a call_node (ie a function call) like this:
    schema = copy.deepcopy(...)
             ^^^^^^^^^^^^^
    Ignore any function calls that are not copy.deepcopy().
    """
    if not (
        isinstance(call_node, nodes.Call)
        and call_node.func.as_string() == "copy.deepcopy"
    ):
        return
    return next(call_node.args[0].infer())


def predicate(cls: nodes.ClassDef) -> bool:
    """
    Astroid (used by pylint) calls this to see if our transform function needs to run.
    """
    if cls.name in CLASS_NAME_SKIPLIST:
        # class looks like an API model class, but it isn't.
        return False

    if not cls.name.endswith("API") and "schema" not in cls.locals:
        # class does not look like an API model class.
        return False

    return True


def transform(cls: nodes.ClassDef):
    """
    Astroid (used by pylint) calls this function on each class definition it discovers.
    cls is an Astroid AST representation of that class.

    Our purpose here is to extract the schema dict from API model classes
    so that we can inform pylint about all of the attributes on those models.
    We do this by injecting attributes on the class for each property in the schema.
    """

    # This is a class which defines attributes in "schema" variable using json schema.
    # Those attributes are then assigned during run time inside the constructor

    # Get the value node for the "schema =" assignment
    schema_dict_node = next(cls.igetattr("schema"))

    extra_schema_properties = {}

    # If the "schema =" assignment's value node is not a simple type (like a dictionary),
    # then pylint cannot infer exactly what it does. Most of the time, this is actually
    # a function call to copy the schema from another class. So, let's find the dictionary.
    if schema_dict_node is astroid.Uninferable:
        # the assignment probably looks like this:
        # schema = copy.deepcopy(ActionAPI.schema)

        # so far we only have the value, but we need the actual assignment
        assigns = [n for n in cls.get_children() if isinstance(n, nodes.Assign)]
        schema_assign_name_node = cls.local_attr("schema")[0]
        schema_assign_node = next(
            assign for assign in assigns if assign.targets[0] == schema_assign_name_node
        )
        assigns.remove(schema_assign_node)

        # We only care about "schema = copy.deepcopy(...)"
        schema_dict_node = infer_copy_deepcopy(schema_assign_node.value)
        if not schema_dict_node:
            # This is not an API model class, as it doesn't have
            # something we can resolve to a dictionary.
            return

        # OK, now we need to look for any properties that dynamically modify
        # the dictionary that was just copied from somewhere else.
        # See the note below for why we only care about "properties" here.
        for assign_node in assigns:
            # we're looking for assignments like this:
            # schema["properties"]["ttl"] = {...}
            target = assign_node.targets[0]
            try:
                if (
                    isinstance(target, nodes.Subscript)
                    and target.value.value.name == "schema"
                ):
                    if (
                        isinstance(target.value.slice.value, nodes.Const)
                        and target.value.slice.value.value == "properties"
                    ):
                        # python <3.9
                        property_name_node = target.slice.value
                    elif (
                        isinstance(target.value.slice, nodes.Const)
                        and target.value.slice.value == "properties"
                    ):
                        # python 3.9+
                        property_name_node = target.slice
                    else:
                        # not schema["properties"]
                        continue
                else:
                    # not schema[...]
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

    # We only care about "properties" in the schema because that's the only part of the schema
    # that gets translated into dynamic attributes on the model API class.
    properties_dict_node = None
    for key_node, value_node in schema_dict_node.items:
        if key_node.value == "properties":
            properties_dict_node = value_node
            break

    if not properties_dict_node and not extra_schema_properties:
        # Not a class we can do anything with
        return

    # Hooray! We have the schema properties dict now, so we can start processing
    # each property and add an attribute for each one to the API model class node.
    for property_name_node, property_data_node in properties_dict_node.items + list(
        extra_schema_properties.items()
    ):
        property_name = property_name_node.value.replace(
            "-", "_"
        )  # Note: We do the same in Python code

        # Despite the processing above to extract the schema properties dictionary
        # each property in the dictionary might also reference other variables,
        # so we still need to resolve these to figure out each property's type.

        # an indirect reference to copy.deepcopy() as in:
        #   REQUIRED_ATTR_SCHEMAS = {"action": copy.deepcopy(ActionAPI.schema)}
        #   schema = {"properties": {"action": REQUIRED_ATTR_SCHEMAS["action"]}}
        if isinstance(property_data_node, nodes.Subscript):
            var_name = property_data_node.value.name
            if isinstance(property_data_node.slice.value, nodes.Const):  # python <3.9
                subscript = property_data_node.slice.value.value
            elif isinstance(property_data_node.slice, nodes.Const):  # python 3.9+
                subscript = property_data_node.slice.value
            else:
                continue

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
            # We have a property schema, but we only care about the property's type.
            for property_key_node, property_value_node in property_data_node.items:
                if property_key_node.value == "type":
                    property_type_node = next(property_value_node.infer())
                    break

        if property_type_node is None and isinstance(
            property_data_node, nodes.Attribute
        ):
            # reference schema from another file like this:
            #   from ... import TriggerAPI
            #   schema = {"properties": {"trigger": TriggerAPI.schema}}
            # We only pull a schema from another file when it is an "object" (a dict).
            # So, we do not need to do any difficult cross-file processing.
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
            # We should only hit this if someone has used a different approach
            # for dynamically constructing the property's schema.
            # Expose the AST at this point to facilitate handling that approach.
            raise Exception(property_type_node.repr_tree())

        # Hooray! We've got a property's name at this point.
        # And we have the property's type, if that type was defined in the schema.
        # Now, we can construct the AST node that we'll add to the API model class.

        if property_type == "object":
            node = nodes.Dict(
                property_data_node.lineno,
                property_data_node.col_offset,
                parent=property_data_node,
                end_lineno=property_data_node.end_lineno,
                end_col_offset=property_data_node.end_col_offset,
            )
        elif property_type == "array":
            node = nodes.List(
                property_data_node.lineno,
                property_data_node.col_offset,
                parent=property_data_node,
                end_lineno=property_data_node.end_lineno,
                end_col_offset=property_data_node.end_col_offset,
            )
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
            node = astroid.ClassDef(
                property_name,
                property_data_node.lineno,
                property_data_node.col_offset,
                parent=property_data_node,
                end_lineno=property_data_node.end_lineno,
                end_col_offset=property_data_node.end_col_offset,
            )

        # Create a "property = node" assign node
        assign_node = nodes.Assign(
            property_name_node.lineno,
            property_name_node.col_offset,
            parent=cls,
            end_lineno=property_data_node.end_lineno,
            end_col_offset=property_data_node.end_col_offset,
        )
        assign_name_node = nodes.AssignName(
            property_name,
            property_name_node.lineno,
            property_name_node.col_offset,
            parent=assign_node,
            end_lineno=property_name_node.end_lineno,
            end_col_offset=property_name_node.end_col_offset,
        )
        assign_node.postinit(
            targets=[assign_name_node], value=node, type_annotation=None
        )

        # Finally, add the property node as an attribute on the class.
        cls.locals[property_name] = [assign_name_node]

    # Now, pylint should be aware of all of the properties that get dynamically
    # added as attributes on the API model class.


MANAGER.register_transform(astroid.ClassDef, transform, predicate)
