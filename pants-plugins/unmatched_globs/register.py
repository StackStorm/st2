from unmatched_globs import target_types_rules
from unmatched_globs.target_types import UnmatchedGlobsTarget


def rules():
    return target_types_rules.rules()


def target_types():
    return [UnmatchedGlobsTarget]
