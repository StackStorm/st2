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

import re
import sys
import os
import platform
import subprocess

from st2common.util.shell import quote_unix

distro = platform.linux_distribution()[0]

if len(sys.argv) < 3:
    raise ValueError('Usage: service.py <action> <service>')

args = {'act': quote_unix(sys.argv[1]), 'service': quote_unix(sys.argv[2])}

if re.search(distro, 'Ubuntu'):
    if os.path.isfile("/etc/init/%s.conf" % args['service']):
        cmd_args = ['service', args['service'], args['act']]
    elif os.path.isfile("/etc/init.d/%s" % args['service']):
        cmd_args = ['/etc/init.d/%s' % (args['service']), args['act']]
    else:
        print("Unknown service")
        sys.exit(2)
elif re.search(distro, 'Redhat') or re.search(distro, 'Fedora') or \
        re.search(distro, 'CentOS Linux'):
    cmd_args = ['systemctl', args['act'], args['service']]

subprocess.call(cmd_args, shell=False)
