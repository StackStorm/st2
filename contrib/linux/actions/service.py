#!/usr/bin/env python

# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
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

"""
NOTE: This script file utilizes remote-shell-script runner which means it copied as-is to the
remote host and executed using Python binary available on that systems.

This means it doesn't use pack or StackStorm specific virtual environment which means we can't
rely on any 3rd party dependencies.
"""

import re
import sys
import os
import platform
import subprocess

from st2common.util.shell import quote_unix


def get_linux_distribution():
    # platform.linux_distribution() is not available in Python >= 3.8
    if hasattr(platform, "linux_distribution"):
        distro = platform.linux_distribution()[0]  # pylint: disable=no-member
    else:
        # Fall back to shelling out to lsb_release
        result = subprocess.run(
            "lsb_release -i -s", shell=True, check=True, stdout=subprocess.PIPE
        )
        distro = result.stdout.decode("utf-8").strip()

    if not distro:
        raise ValueError("Fail to detect distribution we are running on")

    return distro


if len(sys.argv) < 3:
    raise ValueError("Usage: service.py <action> <service>")

distro = get_linux_distribution()

args = {"act": quote_unix(sys.argv[1]), "service": quote_unix(sys.argv[2])}

print("Detected distro: %s" % (distro))

if re.search(distro, "Ubuntu"):
    if os.path.isfile("/etc/init/%s.conf" % args["service"]):
        cmd_args = ["service", args["service"], args["act"]]
    elif os.path.isfile("/etc/init.d/%s" % args["service"]):
        cmd_args = ["/etc/init.d/%s" % (args["service"]), args["act"]]
    else:
        print("Unknown service")
        sys.exit(2)
elif (
    re.search(distro, "Redhat")
    or re.search(distro, "Fedora")
    or re.search(distro, "CentOS")
    or re.search(distro, "Rocky Linux")
):
    cmd_args = ["systemctl", args["act"], args["service"]]

subprocess.call(cmd_args, shell=False)
