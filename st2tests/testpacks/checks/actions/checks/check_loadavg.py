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

from __future__ import absolute_import

import sys


def print_load_avg(args):
    period = args[1]

    loadavg_file = "/proc/loadavg"
    cpuinfo_file = "/proc/cpuinfo"
    cpus = 0

    try:
        fh = open(loadavg_file, "r")
        load = fh.readline().split()[0:3]
        fh.close()
    except:
        sys.stderr.write("Error opening %s\n" % loadavg_file)
        sys.exit(2)

    try:
        fh = open(cpuinfo_file, "r")
        for line in fh:
            if "processor" in line:
                cpus += 1
        fh.close()
    except:
        sys.stderr.write("Error opeing %s\n" % cpuinfo_file)

    one_min = "1 min load/core: %s" % str(float(load[0]) / cpus)
    five_min = "5 min load/core: %s" % str(float(load[1]) / cpus)
    fifteen_min = "15 min load/core: %s" % str(float(load[2]) / cpus)

    if period == "1" or period == "one":
        print(one_min)
    elif period == "5" or period == "five":
        print(five_min)
    elif period == "15" or period == "fifteen":
        print(fifteen_min)
    else:
        print(one_min + " " + five_min + " " + fifteen_min)


if __name__ == "__main__":
    print_load_avg(sys.argv)
