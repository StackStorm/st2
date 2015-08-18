#!/usr/bin/env python

import sys
import json

if len(sys.argv) >= 2:
    time = sys.argv[1]
else:
    time = None

loadAvgFile = "/proc/loadavg"
cpuInfoFile = "/proc/cpuinfo"
cpus = 0
output = {}

try:
    fh = open(loadAvgFile, 'r')
    load = fh.readline().split()[0:3]
except:
    print("Error opening %s" % loadAvgFile)
    sys.exit(2)
finally:
    fh.close()

try:
    fh = open(cpuInfoFile, 'r')
    for line in fh:
        if "processor" in line:
            cpus += 1
except:
    print("Error opening %s" % cpuInfoFile)
    sys.exit(2)
finally:
    fh.close()

output['1'] = str(float(load[0]) / cpus)
output['5'] = str(float(load[1]) / cpus)
output['15'] = str(float(load[2]) / cpus)

if time == '1' or time == 'one':
    print(output['1'])
elif time == '5' or time == 'five':
    print(output['5'])
elif time == '15' or time == 'fifteen':
    print(output['15'])
else:
    print(json.dumps(output))

sys.exit(0)
