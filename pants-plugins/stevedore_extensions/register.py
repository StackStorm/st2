# coding: utf-8

from stevedore_extensions import target_types_rules
from stevedore_extensions.target_types import StevedoreExtension


def rules():
    return [*target_types_rules.rules()]


def target_types():
    return [StevedoreExtension]
