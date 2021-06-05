from pants.engine.target import COMMON_TARGET_FIELDS, Dependencies, StringField, Target


class MessageOnErrorField(StringField):
    alias = "message_on_error"
    required = True
    help = "The message to warn with when the dependency globs do not match."


# See `target_types_rules.py` for a dependency injection rule.
class UnmatchedGlobsDependencies(Dependencies):
    required = True


class UnmatchedGlobsTarget(Target):
    alias = "unmatched_globs"
    core_fields = (*COMMON_TARGET_FIELDS, UnmatchedGlobsDependencies, MessageOnErrorField)
    help = "Declare an error message to show when dependency globs do not match."

