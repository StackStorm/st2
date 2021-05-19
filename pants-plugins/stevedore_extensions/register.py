# coding: utf-8

from pants.backend.codegen import export_codegen_goal

from stevedore_extensions import (
    target_types_rules, rules as stevedore_rules, stevedore_dependency_inference
)
from stevedore_extensions.target_types import StevedoreExtension


# TODO: add the entry_points automatically to setup_py
# TODO: add stevedore_namespaces field to python_sources?


def rules():
    return [
        *target_types_rules.rules(),
        *stevedore_rules.rules(),
        *stevedore_dependency_inference.rules(),
        *export_codegen_goal.rules(),
    ]


def target_types():
    return [StevedoreExtension]
