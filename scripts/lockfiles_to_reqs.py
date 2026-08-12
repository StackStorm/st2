#!/usr/bin/env python
# Copyright 2025 The StackStorm Authors.
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

import copy
import json
import logging
from pathlib import Path

from fixate_requirements import (
    load_fixed_requirements,
    parse_req_from_line,
    write_requirements,
)


LOG = logging.getLogger(__name__)


FIXED_REQUIREMENTS = "fixed-requirements.txt"
TEST_REQUIREMENTS = "test-requirements.txt"
MAKEFILE = "Makefile"

_LOCKFILE = "lockfiles/{resolve}.lock"
TOOL_RESOLVES = ("st2", "bandit", "flake8", "pylint", "black")
# irrelevant resolves: "pants-plugins", "twine"
LOCKFILES = tuple(_LOCKFILE.format(resolve=tool) for tool in TOOL_RESOLVES)


def strip_comments_from_pex_json_lockfile(lockfile_bytes: bytes) -> bytes:
    """
    Copied from code by Pants Project Contributors (Apache 2.0 licensed):
    https://github.com/pantsbuild/pants/blob/release_2.25.0/src/python/pants/backend/python/util_rules/pex_requirements.py#L119-L127

    TODO: delete this once we get rid of the legacy fixate requirements files.
    """
    return b"\n".join(
        line
        for line in lockfile_bytes.splitlines()
        if not line.lstrip().startswith(b"//")
    )


def _update(old_req, name, version):
    parsedreq = parse_req_from_line(old_req.requirement, old_req.line_source)
    assert parsedreq.requirement.name == name
    specs = parsedreq.requirement.specifier
    if len(specs) == 0:
        # name-only dep. Nothing to do. Skipping.
        return None
    elif len(specs) > 1:
        LOG.warning(
            "Cannot automatically update comma separated version specifier: %s", specs
        )
        return None
    spec = tuple(specs)[0]
    if spec.version != version:
        if spec.operator != "==":
            LOG.warning(
                "Cannot safely auto-change version specifier of %s from %s%s to ==%s",
                name,
                spec.operator,
                spec.version,
                version,
            )
        else:
            # only change pins; ignore any version range
            new_spec = spec.__class__(f"=={version}", spec.prereleases or None)
            new_specs = specs.__class__([new_spec], specs.prereleases or None)
            new_req = copy.deepcopy(parsedreq.requirement)
            new_req.specifier = new_specs
            return str(new_req)
    return None


def plan_update(old_reqs, name, version, reqs_updates):
    if name not in old_reqs:
        return
    old_req = old_reqs[name]
    updated_line = _update(old_req, name, version)
    if updated_line is not None:
        reqs_updates[name] = updated_line


def do_updates(path, old_reqs, reqs_updates):
    lines = path.read_text().splitlines()
    for name, updated_line in reqs_updates.items():
        line_source = old_reqs[name].line_source
        # line_source fmt is "line <number> of <file_path>"
        _, line_number, _ = line_source.split(maxsplit=2)
        line_index = int(line_number) - 1
        lines[line_index] = updated_line
    path.write_text("\n".join(lines) + "\n")


def load_makefile_reqs(path):
    lines = path.read_text().splitlines()
    line_prefixes = {"pip": "PIP_VERSION ?= ", "setuptools": "SETUPTOOLS_VERSION ?= "}
    requirements = {"pip": None, "setuptools": None}
    for index, line in enumerate(lines):
        for name, prefix in line_prefixes.items():
            if line.startswith(prefix):
                version = line[len(prefix) :].strip()
                requirements[name] = (index, prefix, version)
        if None not in requirements.values():
            break
    return requirements


def plan_makefile_update(old_reqs, name, version, reqs_updates):
    if name not in old_reqs:
        # this shouldn't happen
        return
    index, prefix, old_version = old_reqs[name]
    if old_version != version:
        reqs_updates[name] = (index, f"{prefix}{version}")


def do_makefile_updates(path, reqs_updates):
    lines = path.read_text().splitlines()
    for name, info in reqs_updates.items():
        index, line = info
        lines[index] = line
    path.write_text("\n".join(lines) + "\n")


def copy_locked_versions_into_legacy_requirements_files():
    fixed_path = Path(FIXED_REQUIREMENTS).resolve()
    test_path = Path(TEST_REQUIREMENTS).resolve()
    makefile_path = Path(MAKEFILE).resolve()

    fixed_reqs = load_fixed_requirements(FIXED_REQUIREMENTS)
    test_reqs = load_fixed_requirements(TEST_REQUIREMENTS)
    makefile_reqs = load_makefile_reqs(makefile_path)
    locked_in_makefile = ("pip", "setuptools")

    fixed_reqs_updates = {}
    test_reqs_updates = {}
    makefile_reqs_updates = {}

    LOG.info("Looking for verion changes")
    handled = []
    for lockfile in LOCKFILES:
        lockfile_bytes = strip_comments_from_pex_json_lockfile(
            Path(lockfile).read_bytes()
        )
        pex_lock = json.loads(lockfile_bytes.decode("utf-8"))
        locked_requirements = pex_lock["locked_resolves"][0]["locked_requirements"]
        locked_reqs_name_version_map = {
            req["project_name"]: req["version"] for req in locked_requirements
        }
        for name, version in locked_reqs_name_version_map.items():
            if name in handled:
                # st2.lock goes first so we can just ignore duplicates from tool lockfiles.
                continue
            plan_update(fixed_reqs, name, version, fixed_reqs_updates)
            plan_update(test_reqs, name, version, test_reqs_updates)
            if name in locked_in_makefile:
                plan_makefile_update(
                    makefile_reqs, name, version, makefile_reqs_updates
                )
            handled.append(name)

    if not fixed_reqs_updates:
        LOG.info("No updates required in %s", FIXED_REQUIREMENTS)
    else:
        LOG.info("Updating %s", FIXED_REQUIREMENTS)
        do_updates(fixed_path, fixed_reqs, fixed_reqs_updates)

    if not test_reqs_updates:
        LOG.info("No updates required in %s", TEST_REQUIREMENTS)
    else:
        LOG.info("Updating %s", TEST_REQUIREMENTS)
        do_updates(test_path, test_reqs, test_reqs_updates)

    if not makefile_reqs_updates:
        LOG.info("No updates required in %s", MAKEFILE)
    else:
        LOG.info("Updating %s", MAKEFILE)
        do_makefile_updates(makefile_path, makefile_reqs_updates)

    LOG.info("Done updating %s and %s", FIXED_REQUIREMENTS, TEST_REQUIREMENTS)


def fixate_legacy_requirements_files():  # based on .requirements Makefile target
    skip = ["virtualenv", "virtualenv-osx"]

    workspace = Path(".")
    sources = list(workspace.glob("st2*/in-requirements.txt"))
    sources.extend(list(workspace.glob("contrib/runners/*/in-requirements.txt")))

    output = "requirements.txt"
    LOG.info(
        "Updating (fixating) %s files with requirements from %s",
        output,
        FIXED_REQUIREMENTS,
    )
    write_requirements(
        sources=[str(source) for source in sources],
        fixed_requirements=FIXED_REQUIREMENTS,
        output_file=output,
        skip=skip,
    )

    for source in sources:
        output = str(source.with_name("requirements.txt"))
        write_requirements(
            sources=[str(source)],
            fixed_requirements=FIXED_REQUIREMENTS,
            output_file=output,
            skip=skip,
        )
    LOG.info("Done updating (fixating) requirements.txt files")


if __name__ == "__main__":
    log_level = logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)s [-] %(message)s", level=log_level
    )
    copy_locked_versions_into_legacy_requirements_files()
    fixate_legacy_requirements_files()
