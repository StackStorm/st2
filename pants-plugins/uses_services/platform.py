import json

from pants.engine.fs import EMPTY_DIGEST, CreateDigest, Digest, FileContent, FileDigest
from pants.engine.process import Process, ProcessCacheScope, ProcessResult
from pants.engine.rules import collect_rules, _uncacheable_rule
from .inspect_platform import Platform

__all__ = ["Platform", "get_platform", "rules"]


@_uncacheable_rule
async def get_platform() -> Platform:

    script_path = "./inspect_platform.py"
    script_digest = await Get(
        Digest,
        # TODO: I need both the script and `distro`, the dependency. Do I need to build a PEX?
        CreateDigest([FileContent(script_path, "", is_executable=True)]),
    )

    result = await Get(
        ProcessResult,
        Process(
            description=f"Introspecting platform (arch, os, distro)",
            input_digest=script_digest,
            argv=[script_path],
            # this can change from run to run, so don't cache results.
            cache_scope=ProcessCacheScope.PER_RESTART,  # NEVER?
        ),
    )
    platform = json.loads(result.stdout)
    return Platform(**platform)


def rules():
    return collect_rules()
