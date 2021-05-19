import json

from pants.backend.python.util_rules.pex import (
    PexRequest,
    PexRequirements,
    VenvPex,
    VenvPexProcess,
)
from pants.engine.fs import CreateDigest, Digest, FileContent
from pants.engine.process import ProcessCacheScope, ProcessResult
from pants.engine.rules import collect_rules, Get, rule
from pants.util.logging import LogLevel
from .inspect_platform import Platform, __file__ as inspect_platform_full_path

__all__ = ["Platform", "get_platform", "rules"]


@rule
async def get_platform() -> Platform:

    distro_pex = await Get(
        VenvPex,
        PexRequest(
            output_filename="distro.pex",
            internal_only=True,
            requirements=[PexRequirements({"distro"})],
        ),
    )

    script_path = "./inspect_platform.py"

    # pants is already watching this directory as it is under a source root.
    # So, we don't need to double watch with PathGlobs, just open it.
    with open(inspect_platform_full_path, "rb") as script_file:
        script_contents = script_file.read()

    script_digest = await Get(
        Digest,
        CreateDigest([FileContent(script_path, script_contents)]),
    )

    result = await Get(
        ProcessResult,
        VenvPexProcess(
            distro_pex,
            argv=[script_path],
            input_digest=script_digest,
            description=f"Introspecting platform (arch, os, distro)",
            # this can change from run to run, so don't cache results.
            cache_scope=ProcessCacheScope.PER_RESTART,  # NEVER?
            level=LogLevel.DEBUG,
        ),
    )
    platform = json.loads(result.stdout)
    return Platform(**platform)


def rules():
    return collect_rules()
