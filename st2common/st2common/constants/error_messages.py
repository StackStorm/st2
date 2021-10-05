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

__all__ = ["PACK_VIRTUALENV_DOESNT_EXIST", "PYTHON2_DEPRECATION"]

PACK_VIRTUALENV_DOESNT_EXIST = """
The virtual environment (%(virtualenv_path)s) for pack "%(pack)s" does not exist. Normally this is
created when you install a pack using "st2 pack install". If you installed your pack by some other
means, you can create a new virtual environment using the command:
"st2 run packs.setup_virtualenv packs=%(pack)s"
"""

PYTHON2_DEPRECATION = (
    "DEPRECATION WARNING. Support for python 2 will be removed in future "
    "StackStorm releases. Please ensure that all packs used are python "
    "3 compatible. Your StackStorm installation may be upgraded from "
    "python 2 to python 3 in future platform releases. It is recommended "
    "to plan the manual migration to a python 3 native platform, e.g. "
    "Ubuntu 18.04 LTS or CentOS/RHEL 8."
)
