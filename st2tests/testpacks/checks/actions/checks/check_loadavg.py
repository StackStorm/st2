#!/usr/bin/python

from __future__ import absolute_import
import sys


def print_load_avg(args):
    period = args[1]

    loadavg_file = '/proc/loadavg'
    cpuinfo_file = '/proc/cpuinfo'
    cpus = 0

    try:
        fh = open(loadavg_file, 'r')
        load = fh.readline().split()[0:3]
        fh.close()
    except:
        sys.stderr.write('Error opening %s\n' % loadavg_file)
        sys.exit(2)

    try:
        fh = open(cpuinfo_file, 'r')
        for line in fh:
            if 'processor' in line:
                cpus += 1
        fh.close()
    except:
        sys.stderr.write('Error opeing %s\n' % cpuinfo_file)

    one_min = '1 min load/core: %s' % str(float(load[0]) / cpus)
    five_min = '5 min load/core: %s' % str(float(load[1]) / cpus)
    fifteen_min = '15 min load/core: %s' % str(float(load[2]) / cpus)

    if period == '1' or period == 'one':
        print(one_min)
    elif period == '5' or period == 'five':
        print(five_min)
    elif period == '15' or period == 'fifteen':
        print(fifteen_min)
    else:
        print(one_min + " " + five_min + " " + fifteen_min)


if __name__ == '__main__':
    print_load_avg(sys.argv)
