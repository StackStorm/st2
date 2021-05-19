# coding: utf-8

from pants.backend.codegen import export_codegen_goal

from stevedore_extensions import target_types_rules, rules as stevedore_rules
from stevedore_extensions.target_types import StevedoreExtension


def rules():
    return [
        *target_types_rules.rules(),
        *stevedore_rules.rules(),
        *export_codegen_goal.rules(),
    ]


def target_types():
    return [StevedoreExtension]
