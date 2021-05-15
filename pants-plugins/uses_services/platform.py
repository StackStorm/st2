import json

from pants.backend.python.util_rules.pex import (
    PexRequest,
    PexRequirements,
    VenvPex,
    VenvPexProcess,
)
from pants.engine.fs import EMPTY_DIGEST, CreateDigest, Digest, FileContent, FileDigest
from pants.engine.process import Process, ProcessCacheScope, ProcessResult
from pants.engine.rules import collect_rules, _uncacheable_rule
from pants.util.logging import LogLevel
from .inspect_platform import Platform

__all__ = ["Platform", "get_platform", "rules"]


@_uncacheable_rule
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
    script_digest = await Get(
        Digest,
        # TODO: get script contents
        CreateDigest([FileContent(script_path, "", is_executable=True)]),
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
            level=LogLevl.DEBUG,
        ),
    )
    platform = json.loads(result.stdout)
    return Platform(**platform)


def rules():
    return collect_rules()
