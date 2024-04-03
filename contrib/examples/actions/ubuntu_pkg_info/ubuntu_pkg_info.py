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

import shlex
import sys
import subprocess

import six
import lib.datatransformer as transformer  # pylint:disable=import-error,no-name-in-module


def main(args):
    command_list = shlex.split("apt-cache policy " + " ".join(args[1:]))
    process = subprocess.Popen(
        command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    command_stdout, command_stderr = process.communicate()
    command_exitcode = process.returncode
    try:
        payload = transformer.to_json(command_stdout, command_stderr, command_exitcode)
    except Exception as e:
        sys.stderr.write("JSON conversion failed. %s" % six.text_type(e))
        sys.exit(1)

    sys.stdout.write(payload)


if __name__ == "__main__":
    main(sys.argv)
