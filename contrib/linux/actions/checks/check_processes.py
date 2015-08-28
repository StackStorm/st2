#!/usr/bin/env python

import os
import sys
import re
import json


class CheckProcs(object):
    myPid = 0
    state = ""
    name = ""
    pid = 0
    allProcs = []
    interestingProcs = []
    procDir = "/proc"
    debug = False

    def __init__(self):
        self.myPid = os.getpid()

    def setup(self, debug=False, pidlist=False):
        self.debug = debug
        self.pidlist = pidlist

        if debug is True:
            print("Debug is on")

        self.allProcs = [procs for procs in os.listdir(self.procDir) if procs.isdigit() and
                         int(procs) != int(self.myPid)]

    def process(self, criteria):
        for p in self.allProcs:
            try:
                fh = open(self.procDir + "/" + p + "/stat")
                pInfo = fh.readline().split()
                cmdfh = open(self.procDir + "/" + p + "/cmdline")
                cmd = cmdfh.readline()
                pInfo[1] = cmd
            except:
                continue
            finally:
                cmdfh.close()
                fh.close()

            if criteria == 'state':
                if pInfo[2] == self.state:
                    self.interestingProcs.append(pInfo)
            elif criteria == 'name':
                if re.search(self.name, pInfo[1]):
                    self.interestingProcs.append(pInfo)
            elif criteria == 'pid':
                if pInfo[0] == self.pid:
                    self.interestingProcs.append(pInfo)

    def byState(self, state):
        self.state = state
        self.process(criteria='state')
        self.show()

    def byPid(self, pid):
        self.pid = pid
        self.process(criteria='pid')
        self.show()

    def byName(self, name):
        self.name = name
        self.process(criteria='name')
        self.show()

    def run(self, foo, criteria):
        if foo == 'state':
            self.byState(criteria)
        elif foo == 'name':
            self.byName(criteria)
        elif foo == 'pid':
            self.byPid(criteria)

    def show(self):
        prettyOut = {}
        if len(self.interestingProcs) > 0:
            for proc in self.interestingProcs:
                #  prettyOut += "%s %s - time:%s\n" % (proc[0],proc[1],proc[13])
                prettyOut[proc[0]] = proc[1]

        if self.pidlist is True:
            pidlist = ' '.join(prettyOut.keys())
            sys.stderr.write(pidlist)

        print(json.dumps(prettyOut))


if __name__ == '__main__':
    if "pidlist" in sys.argv:
        pidlist = True
    else:
        pidlist = False

    foo = CheckProcs()
    foo.setup(debug=False, pidlist=pidlist)
    foo.run(sys.argv[1], sys.argv[2])
