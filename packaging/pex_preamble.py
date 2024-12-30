# Copyright 2024 The StackStorm Authors.
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

import os
import sys

# This check makes re-exec safe by ensuring we modify env+argv once.
if os.environ.pop("ST2_PEX_EXTRACT", "0") not in ("1", "skip"):
    os.environ["ST2_PEX_EXTRACT"] = "1"

    st2_config_path = os.environ.get("ST2_CONFIG_PATH", os.environ.get("ST2_CONF")) or "/etc/st2/st2.conf"

    # late import to minimize re-exec overhead (oslo_config is not available yet, so use stdlib here)
    import configparser

    conf = configparser.ConfigParser()
    conf.read_dict({"system": {"base_path": "/opt/stackstorm"}})
    conf.read(st2_config_path)
    st2_base_path = conf.get("system", "base_path")
    st2_base_path = os.environ.pop("ST2_SYSTEM__BASE_PATH", st2_base_path)

    st2_venv = os.path.join(st2_base_path, "st2")
    if os.path.exists(st2_venv):
        print(f"WARNING: This will overwrite {st2_venv}", file=sys.stderr)

    # This env var and sys.argv will create a venv in the st2_venv dir.
    os.environ["PEX_TOOLS"] = "1"
    sys.argv[1:1] = (
        "venv",
        "--force",  # remove and replace the venv if it exists
        "--non-hermetic-scripts",  # do not add -sE to python shebang
        "--system-site-packages",
        "--prompt=st2",
        st2_venv,
    )

# The standard PEX bootstrap code is below this line.
