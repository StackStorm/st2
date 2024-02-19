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
    fh = open(loadAvgFile, "r")
    load = fh.readline().split()[0:3]
except:
    print("Error opening %s" % loadAvgFile)
    sys.exit(2)
finally:
    fh.close()

try:
    fh = open(cpuInfoFile, "r")
    for line in fh:
        if "processor" in line:
            cpus += 1
except:
    print("Error opening %s" % cpuInfoFile)
    sys.exit(2)
finally:
    fh.close()

output["1"] = str(float(load[0]) / cpus)
output["5"] = str(float(load[1]) / cpus)
output["15"] = str(float(load[2]) / cpus)

if time == "1" or time == "one":
    print(output["1"])
elif time == "5" or time == "five":
    print(output["5"])
elif time == "15" or time == "fifteen":
    print(output["15"])
else:
    print(json.dumps(output))

sys.exit(0)
