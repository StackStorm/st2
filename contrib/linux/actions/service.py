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

import re
import sys
import os
import platform
import subprocess

distro = platform.linux_distribution()[0]

args = {'act': sys.argv[1], 'service': sys.argv[2]}

if re.search(distro, 'Ubuntu'):
    if os.path.isfile("/etc/init/%s.conf" % args['service']):
        cmd = args['act'] + " " + args['service']
    elif os.path.isfile("/etc/init.d/%s" % args['service']):
        cmd = "/etc/init.d/%s %s" % (args['service'], args['act'])
    else:
        print("Unknown service")
        sys.exit(2)
elif re.search(distro, 'Redhat') or re.search(distro, 'Fedora') or \
        re.search(distro, 'CentOS Linux'):
    cmd = "systemctl %s %s" % (args['act'], args['service'])

subprocess.call(cmd, shell=True)
