#!/usr/bin/env python

import os
import os.path
import sys
import pprint
from urlparse import urlparse
from distutils.version import StrictVersion
from setuptools import setup, find_packages


cwd = os.path.abspath(os.getcwd())
FIXED_REQF = os.path.join(cwd, '../fixed-requirements.txt')
LOCAL_REQF = os.path.join(cwd, 'requirements.txt')
GET_PIP = "    curl https://bootstrap.pypa.io/get-pip.py | python"

try:
    import pip
    from pip.req import parse_requirements
except ImportError:
    print "Download pip:\n", GET_PIP
    sys.exit(1)


def check_pip_version():
    if StrictVersion(pip.__version__) < StrictVersion('7.0.0'):
        print "Upgrade pip, your version `{}' "\
              "is outdated:\n".format(pip.__version__), GET_PIP
        sys.exit(1)


def check_requiremnts_sources():
    for f in (FIXED_REQF, LOCAL_REQF):
        if not os.path.exists(f):
            print "Error: file `{}' not found".format(f)
            sys.exit(1)


def load_requirements(file_path):
    return tuple((r for r in parse_requirements(file_path, session=False)))


def fixate():
    local_reqs = load_requirements(LOCAL_REQF)
    fixed_reqs = load_requirements(FIXED_REQF)

    with open("final-requirements.txt", "w") as f:
        f.write("# Don't edit this file. It's generated automatically!\n")
        for req in local_reqs:
            # we don't have any idea how to process links, so just add them
            if req.link:
                rline = str(req.link) + "\n"
            elif req.req:
                fixed = next((r for r in fixed_reqs if r.req.project_name
                              == req.req.project_name), None)
                rline = (str(fixed.req) if fixed else str(req.req)) + "\n"
            else:
                raise RuntimeError("Unexpected requirement {}".format(req))
            f.write(rline)


if __name__ == "__main__":
    check_pip_version()
    check_requiremnts_sources()
    fixate()
