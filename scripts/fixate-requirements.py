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

"""
This script is used to automate generation of requirements.txt for st2 components.

The idea behind this script is that that each component has it's own requirements
"in-requirements.txt" file. in-requirements.txt is an input requirements file -
a requirements file with dependencies but WITHOUT any version restrictions.

In addition to this file, there's also the top-level "fixed-requirements.txt"
which pins production versions for the whole st2 stack. During production use
(building, packaging, etc) requirements.txt is generated from in-requirements.txt
where version of packages are fixed according to fixed-requirements.txt.
"""

import argparse
import os
import os.path
import sys
from distutils.version import StrictVersion

OSCWD = os.path.abspath(os.curdir)
GET_PIP = '    curl https://bootstrap.pypa.io/get-pip.py | python'

try:
    import pip
    from pip.req import parse_requirements
except ImportError:
    print 'Download pip:\n', GET_PIP
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description='Tool for requirements.txt generation.')
    parser.add_argument('-s', '--source-requirements', nargs='+',
                        required=True,
                        help='Specify paths to requirements file(s). '
                        'In case several requirements files are given their content is merged.')
    parser.add_argument('-f', '--fixed-requirements', required=True,
                        help='Specify path to fixed-requirements.txt file.')
    parser.add_argument('-o', '--output-file', default='requirements.txt',
                        help='Specify path to the resulting requirements file.')
    parser.add_argument('--skip', default=None,
                        help=('Comma delimited list of requirements to not '
                              'include in the generated file.'))
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)
    return vars(parser.parse_args())


def check_pip_version():
    if StrictVersion(pip.__version__) < StrictVersion('6.1.0'):
        print "Upgrade pip, your version `{0}' "\
              "is outdated:\n".format(pip.__version__), GET_PIP
        sys.exit(1)


def load_requirements(file_path):
    return tuple((r for r in parse_requirements(file_path, session=False)))


def locate_file(path, must_exist=False):
    if not os.path.isabs(path):
        path = os.path.join(OSCWD, path)
    if must_exist and not os.path.isfile(path):
        print("Error: couldn't locate file `{0}'".format(path))
    return path


def merge_source_requirements(sources):
    """
    Read requirements source files and merge it's content.
    """
    projects = set()
    merged_requirements = []
    for infile_path in (locate_file(p, must_exist=True) for p in sources):
        for req in load_requirements(infile_path):
            # Requirements starting with project name "project ..."
            if req.req:
                # Skip already added project name
                if req.name in projects:
                    continue
                projects.add(req.name)
                merged_requirements.append(req)

            # Requirements lines like "vcs+proto://url"
            elif req.link:
                merged_requirements.append(req)
            else:
                raise RuntimeError('Unexpected requirement {0}'.format(req))

    return merged_requirements


def write_requirements(sources=None, fixed_requirements=None, output_file=None,
                       skip=None):
    """
    Write resulting requirements taking versions from the fixed_requirements.
    """
    skip = skip or []

    requirements = merge_source_requirements(sources)
    fixed = load_requirements(locate_file(fixed_requirements, must_exist=True))

    # Make sure there are no duplicate / conflicting definitions
    fixedreq_hash = {}
    for req in fixed:
        project_name = req.name

        if not req.req:
            continue

        if project_name in fixedreq_hash:
            raise ValueError('Duplicate definition for dependency "%s"' % (project_name))

        fixedreq_hash[project_name] = req

    lines_to_write = []
    links = set()
    for req in requirements:
        if req.name in skip:
            continue

        # we don't have any idea how to process links, so just add them
        if req.link and req.link not in links:
            links.add(req.link)
            rline = str(req.link)
        elif req.req:
            project = req.name
            if project in fixedreq_hash:
                rline = str(fixedreq_hash[project].req)
            else:
                rline = str(req.req)

        lines_to_write.append(rline)

    # Sort the lines to guarantee a stable order
    lines_to_write = sorted(lines_to_write)
    data = '\n'.join(lines_to_write) + '\n'
    with open(output_file, 'w') as fp:
        fp.write('# Don\'t edit this file. It\'s generated automatically!\n')
        fp.write(data)

    print('Requirements written to: {0}'.format(output_file))


if __name__ == '__main__':
    check_pip_version()
    args = parse_args()

    if args['skip']:
        skip = args['skip'].split(',')
    else:
        skip = None

    write_requirements(sources=args['source_requirements'],
                       fixed_requirements=args['fixed_requirements'],
                       output_file=args['output_file'],
                       skip=skip)
