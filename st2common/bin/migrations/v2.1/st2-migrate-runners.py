#!/usr/bin/env python
# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from eventlet.green import subprocess

from st2common.util.green.shell import run_command


def main():
    timeout = 180

    args = [
        'st2ctl',
        'reload',
        '--register-all',
        '--register-fail-on-failure'
    ]

    exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE, shell=False,
                                                       timeout=timeout)
    if timed_out:
        print('Timed out migrating runners!')
        sys.exit(1)

    if exit_code == 0:
        print('Migrated runners successfully! Run `st2 runner list` to see available runners.')
    else:
        print('Error migrating runners! ' + \
              'exit code: %d\n\nstderr: %s\n\nstdout: %s\n\n' % (exit_code, stderr, stdout))
        sys.exit(exit_code)

if __name__ == '__main__':
    main()
