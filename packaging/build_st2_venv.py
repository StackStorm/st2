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

# NOTE: In this script, all 3rd party deps are available thanks to pex.
# Do not import any st2 code to avoid polluting the pex with extra files
# (Pants uses dependency inference to add sources beyond our wheels).

import os
import sys
import subprocess

from pathlib import Path
from typing import List, Optional

from oslo_config import cfg


def get_pex_path() -> str:
    return os.environ.get("PEX", sys.argv[0])


def get_st2_base_path(args: Optional[List[str]] = None) -> Path:
    st2_config_path = (
        os.environ.get("ST2_CONFIG_PATH", os.environ.get("ST2_CONF"))
        or "/etc/st2/st2.conf"
    )

    cfg.CONF.register_opts(
        [cfg.StrOpt("base_path", default="/opt/stackstorm")], group="system"
    )

    try:
        cfg.CONF(args=args, default_config_files=[st2_config_path], use_env=False)
    except cfg.ConfigFilesNotFoundError:
        pass

    st2_base_path = os.environ.get(
        "ST2_SYSTEM__BASE_PATH", cfg.CONF["system"]["base_path"]
    )
    return Path(st2_base_path)


def unpack_venv(st2_venv_path: Path) -> int:
    if st2_venv_path.exists():
        print(f"WARNING: This will overwrite {st2_venv_path}", file=sys.stderr)

    env = {"PEX_TOOLS": "1"}
    cmd = [
        get_pex_path(),
        "venv",
        "--force",  # remove and replace the venv if it exists
        "--non-hermetic-scripts",  # do not add -sE to python shebang
        # st2-packages has a note about python symlinks breaking pack install.
        # uncomment this if that proves to still be an issue.
        # "--copies",  # pack install follows python symlinks to find bin dir
        "--system-site-packages",
        "--compile",  # pre-compile all pyc files
        "--prompt=st2",
        str(st2_venv_path),
    ]
    pretty_cmd = "".join(k + "=" + v + " " for k, v in env.items()) + " ".join(cmd)
    print(f"Now running: {pretty_cmd}", file=sys.stderr)

    result = subprocess.call(cmd, env=env)

    if result == 0:
        print(f"Successfully unpacked venv to {st2_venv_path}", file=sys.stderr)
    else:
        print(
            f"Encountered an error unpacking venv to {st2_venv_path}", file=sys.stderr
        )

    return result


def tidy_venv(st2_venv_path: Path) -> None:
    """Clean up and remove this script from the venv.

    Unfortunately, the way pants uses pex, this script ends up in the venv.
    """
    for path in (st2_venv_path / "lib").glob("python*"):
        script_path = path / "site-packages" / "packaging" / "build_st2_venv.py"
        if script_path.exists():
            script_path.unlink()

        script_path = path / "site-packages" / "__pex_executable__.py"
        if script_path.exists():
            script_path.unlink()

    # and remove the reference to this script
    main_path = st2_venv_path / "__main__.py"
    main_path.write_text(main_path.read_text().replace("__pex_executable__", ""))


def main() -> int:
    st2_base_path = get_st2_base_path(sys.argv[1:])
    st2_venv_path = st2_base_path / "st2"

    if not os.access(st2_base_path, os.W_OK):
        print(
            f"ERROR: venv parent directory is not writable: {st2_base_path}",
            file=sys.stderr,
        )
        return 1

    venv_result = unpack_venv(st2_venv_path)
    tidy_venv(st2_venv_path)

    return venv_result


if __name__ == "__main__":
    sys.exit(main())
