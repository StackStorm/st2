from dataclasses import dataclass

from pants.engine.rules import collect_rules, _uncacheable_rule


@dataclass(frozen=True)
class Platform:
    os: str
    arch: str
    # etc


@_uncacheable_rule
async def get_platform() -> Platform:
    # TODO: lookup details (use Process if needed, but prefer python's introspection)
    return Platform("", "")


def rules():
    return collect_rules()
