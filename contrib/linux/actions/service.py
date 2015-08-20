#!/usr/bin/env python

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
elif re.search(distro, 'Redhat') or re.search(distro, 'Fedora'):
    cmd = "systemctl %s %s" % (args['act'], args['service'])

subprocess.call(cmd, shell=True)
