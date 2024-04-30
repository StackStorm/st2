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

from collections.abc import Collection

import astroid
from astroid import parse, nodes

import pylint.checkers.typecheck
import pylint.testutils
from pylint.interfaces import Confidence

# merely importing this registers it in astroid
# so parse() will use our predicate and transform functions.
try:
    # TODO: remove this once we remove the Makefile
    from . import api_models

    FIXTURE_MODULE_ACTION = "pylint_plugins.fixtures.api_models"
    FIXTURE_MODULE_TRIGGER = "pylint_plugins.fixtures.api_models"
except ImportError:
    # pylint_plugins is on PYTHONPATH
    import api_models

    FIXTURE_MODULE_ACTION = "fixtures.api_models"
    FIXTURE_MODULE_TRIGGER = "fixtures.api_models"


def test_skiplist_class_gets_skipped():
    # roughly based on st2api/st2api/controllers/v1/actionexecutions.py
    code = """
    class ActionExecutionReRunController(object):
        class ExecutionSpecificationAPI(object):
            schema = {"properties": {"action": {}}}
    """

    res = parse(code)

    # this serves to document what res is
    assert isinstance(res, nodes.Module)
    assert isinstance(res.body, Collection)
    assert isinstance(res.body[0], nodes.ClassDef)

    class_node: nodes.ClassDef = res.body[0].body[0]
    assert isinstance(class_node, nodes.ClassDef)

    # this was a skiplisted class
    assert class_node.name in api_models.CLASS_NAME_SKIPLIST

    # only schema is present, so no other properties have been added.
    assert len(class_node.body) == 1
    assert "schema" in class_node.locals
    assert "action" not in class_node.locals

    assign_node: nodes.Assign = class_node.body[0]
    assert isinstance(assign_node, nodes.Assign)
    assert isinstance(assign_node.value, nodes.Dict)


def test_non_api_class_gets_skipped():
    code = """
    class ActionExecutionReRunController(object):
        pass
    """

    res = parse(code)

    assert isinstance(res, nodes.Module)

    class_node: nodes.ClassDef = res.body[0]
    assert isinstance(class_node, nodes.ClassDef)

    assert len(class_node.body) == 1
    assert isinstance(class_node.body[0], nodes.Pass)


def test_simple_schema():
    code = """
    class ActionAPI(object):
        schema = {"properties": {"action": {}}}
    """

    res = parse(code)

    assert isinstance(res, nodes.Module)

    class_node: nodes.ClassDef = res.body[0]
    assert isinstance(class_node, nodes.ClassDef)

    # action property added
    assert "schema" in class_node.locals
    assert "action" in class_node.locals
    assert isinstance(class_node.locals["action"][0], nodes.AssignName)
    assert class_node.locals["action"][0].name == "action"


def test_copied_schema():
    code = """
    import copy

    class ActionAPI(object):
        schema = {"properties": {"action": {}}}

    class ActionCreateAPI(object):
        schema = copy.deepcopy(ActionAPI.schema)
        schema["properties"]["default_files"] = {}
    """

    res = parse(code)

    assert isinstance(res, nodes.Module)

    class1_node: nodes.ClassDef = res.body[1]
    assert isinstance(class1_node, nodes.ClassDef)

    assert "schema" in class1_node.locals

    # action property added but not property from the other class
    assert "action" in class1_node.locals
    assert "default_files" not in class1_node.locals

    class2_node: nodes.ClassDef = res.body[2]
    assert isinstance(class2_node, nodes.ClassDef)

    # action (copied) and default_files (added) properties added
    assert "schema" in class2_node.locals
    assert "action" in class2_node.locals
    assert "default_files" in class2_node.locals


def test_copied_imported_schema():
    code = """
    import copy
    from %s import ActionAPI

    class ActionCreateAPI(object):
        schema = copy.deepcopy(ActionAPI.schema)
        schema["properties"]["default_files"] = {}
    """
    code = code % FIXTURE_MODULE_ACTION

    res = parse(code)

    assert isinstance(res, nodes.Module)

    class_node: nodes.ClassDef = res.body[2]
    assert isinstance(class_node, nodes.ClassDef)

    assert "schema" in class_node.locals

    # check for some of the attributes copied from ActionAPI schema
    assert "name" in class_node.locals
    assert "description" in class_node.locals
    assert "runner_type" in class_node.locals

    # check our added property
    assert "default_files" in class_node.locals


def test_indirect_copied_schema():
    code = """
    import copy
    from %s import ActionAPI

    REQUIRED_ATTR_SCHEMAS = {"action": copy.deepcopy(ActionAPI.schema)}

    class ExecutionAPI(object):
        schema = {"properties": {"action": REQUIRED_ATTR_SCHEMAS["action"]}}
    """
    code = code % FIXTURE_MODULE_ACTION

    res = parse(code)

    assert isinstance(res, nodes.Module)

    class_node: nodes.ClassDef = res.body[3]
    assert isinstance(class_node, nodes.ClassDef)

    assert "schema" in class_node.locals
    assert "action" in class_node.locals

    attribute_value_node = next(class_node.locals["action"][0].infer())
    assert isinstance(attribute_value_node, nodes.Dict)


def test_inlined_schema():
    code = """
    from %s import TriggerAPI

    class ActionExecutionAPI(object):
        schema = {"properties": {"trigger": TriggerAPI.schema}}
    """
    code = code % FIXTURE_MODULE_TRIGGER

    res = parse(code)

    assert isinstance(res, nodes.Module)

    class_node: nodes.ClassDef = res.body[1]
    assert isinstance(class_node, nodes.ClassDef)

    assert "schema" in class_node.locals
    assert "trigger" in class_node.locals

    attribute_value_node = next(class_node.locals["trigger"][0].infer())
    assert isinstance(attribute_value_node, nodes.Dict)


def test_property_types():
    code = """
    class RandomAPI(object):
        schema = {
            "properties": {
                "thing": {"type": "object"},
                "things": {"type": "array"},
                "count": {"type": "integer"},
                "average": {"type": "number"},
                "magic": {"type": "string"},
                "flag": {"type": "boolean"},
                "nothing": {"type": "null"},
                "unknown_type": {"type": "world"},
                "undefined_type": {},
            }
        }
    """

    res = parse(code)

    assert isinstance(res, nodes.Module)

    class_node: nodes.ClassDef = res.body[0]
    assert isinstance(class_node, nodes.ClassDef)

    assert "schema" in class_node.locals

    expected = {
        "thing": nodes.Dict,
        "things": nodes.List,
        "unknown_type": nodes.ClassDef,
        "undefined_type": nodes.ClassDef,
    }
    for property_name, value_class in expected.items():
        assert property_name in class_node.locals
        attribute_value_node = next(class_node.locals[property_name][0].infer())
        assert isinstance(attribute_value_node, value_class)

    # simple types (int, str, etc) are a little different
    expected = {
        "count": "int",
        "average": "float",
        "magic": "str",
        "flag": "bool",
    }
    for property_name, value_class_name in expected.items():
        assert property_name in class_node.locals
        attribute_value_node = next(class_node.locals[property_name][0].infer())
        assert isinstance(attribute_value_node, nodes.ClassDef)
        assert attribute_value_node.name == value_class_name

    # and None does its own thing too
    assert "nothing" in class_node.locals
    attribute_value_node = next(class_node.locals["nothing"][0].infer())
    assert isinstance(attribute_value_node, nodes.Const)
    assert attribute_value_node.value is None


class TestTypeChecker(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint.checkers.typecheck.TypeChecker
    checker: pylint.checkers.typecheck.TypeChecker

    def test_finds_no_member_on_api_model_when_property_not_in_schema(self):
        # The "#@" tells astroid which nodes to extract
        assign_node_present, assign_node_missing = astroid.extract_node(
            """
            class TestAPI:
                schema = {"properties": {"present": {"type": "string"}}}

            def test():
                model = TestAPI()
                present = model.present  #@
                missing = model.missing  #@
            """
        )

        self.checker.visit_assign(assign_node_present)
        self.checker.visit_assign(assign_node_missing)

        # accessing a property defined in the schema
        with self.assertNoMessages():
            self.checker.visit_attribute(assign_node_present.value)

        # accessing a property NOT defined in the schema
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="no-member",  # E1101
                args=("Instance of", "TestAPI", "missing", ""),
                node=assign_node_missing.value,
                line=assign_node_missing.value.lineno,
                col_offset=assign_node_missing.value.col_offset,
                end_line=assign_node_missing.value.end_lineno,
                end_col_offset=assign_node_missing.value.end_col_offset,
                confidence=Confidence(
                    name="INFERENCE", description="Warning based on inference result."
                ),
            )
        ):
            self.checker.visit_attribute(assign_node_missing.value)
