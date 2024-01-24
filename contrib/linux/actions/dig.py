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

import errno
import locale
import subprocess
import random
import sys

from st2common.runners.base_action import Action


class DigAction(Action):
    def run(self, rand, count, nameserver, hostname, queryopts, querytype):
        opt_list = []
        output = []

        cmd_args = ["dig"]
        if nameserver:
            nameserver = "@" + nameserver
            cmd_args.append(nameserver)

        if isinstance(queryopts, str) and "," in queryopts:
            opt_list = queryopts.split(",")
        else:
            opt_list.append(queryopts)

        cmd_args.extend(["+" + option for option in opt_list])

        cmd_args.append(hostname)
        cmd_args.append(querytype)

        try:
            raw_result = subprocess.Popen(
                cmd_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE
            ).communicate()[0]

            if sys.version_info >= (3,):
                # This function might call getpreferred encoding unless we pass
                # do_setlocale=False.
                encoding = locale.getpreferredencoding(do_setlocale=False)
                result_list_str = raw_result.decode(encoding)
            else:
                result_list_str = str(raw_result)

            # Better format the output when the type is TXT
            if querytype.lower() == "txt":
                result_list_str = result_list_str.replace('"', "")

            result_list = list(filter(None, result_list_str.split("\n")))

        # NOTE: Python3 supports the FileNotFoundError, the errono.ENOENT is for py2 compat
        # for Python3:
        # except FileNotFoundError as e:
        except OSError as e:
            if e.errno == errno.ENOENT:
                return (
                    False,
                    "Can't find dig installed in the path (usually /usr/bin/dig). If "
                    "dig isn't installed, you can install it with 'sudo yum install "
                    "bind-utils' or 'sudo apt install dnsutils'",
                )
            else:
                raise e

        if int(count) > len(result_list) or count <= 0:
            count = len(result_list)

        output = result_list[0:count]
        if rand is True:
            random.shuffle(output)
        return output
