from __future__ import absolute_import, print_function

import glob
import os
import os.path
import sys

from distutils.version import StrictVersion

from invoke import run, task

# NOTE: This script can't rely on any 3rd party dependency so we need to use this code here
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
else:
    text_type = unicode

OSCWD = os.path.abspath(os.curdir)
GET_PIP = '    curl https://bootstrap.pypa.io/get-pip.py | python'

try:
    import pip
    from pip import __version__ as pip_version
except ImportError as e:
    print('Failed to import pip: %s' % (text_type(e)))
    print('')
    print('Download pip:\n%s' % (GET_PIP))
    sys.exit(1)

try:
    # pip < 10.0
    from pip.req import parse_requirements
except ImportError:
    # pip >= 10.0

    try:
        from pip._internal.req.req_file import parse_requirements
    except ImportError as e:
        print('Failed to import parse_requirements from pip: %s' % (text_type(e)))
        print('Using pip: %s' % (str(pip_version)))
        sys.exit(1)


# Lifted straight from fixate-requirements.py
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

            if req.editable:
                rline = '-e %s' % (rline)
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
        fp.write('# If you want to update global dependencies, modify fixed-requirements.txt\n')
        fp.write('# and then run \'make requirements\' to update requirements.txt for all\n')
        fp.write('# components.\n')
        fp.write('# If you want to update depdencies for a single component, modify the\n')
        fp.write('# in-requirements.txt for that component and then run \'make requirements\' to\n')
        fp.write('# update the component requirements.txt\n')
        fp.write(data)

    print('Requirements written to: {0}'.format(output_file))


@task
def root_requirements(ctx):
    # Generate all requirements to support current CI pipeline.
    ignore_virtualenvs = list(glob.glob('virtualenv*'))
    component_requirements = list(glob.glob('st2*/in-requirements.txt'))
    runner_requirements = list(glob.glob('contrib/runners/*/in-requirements.txt'))
    write_requirements(skip=ignore_virtualenvs,
                       sources=component_requirements+runner_requirements,
                       fixed_requirements='fixed-requirements.txt',
                       output_file='requirements.txt')


@task
def component_requirements(ctx):
    ignore_virtualenvs = list(glob.glob('virtualenv*'))
    # Generate all requirements to support current CI pipeline.
    for component in list((set(glob.glob("st2*")) | set(glob.glob("contrib/runners/*"))) - set(glob.glob('*.egg-info'))):
        print("===========================================================\n"
              "Generating requirements for {component}\n"
              "==========================================================="
              .format(component=component))
        write_requirements(skip=ignore_virtualenvs,
                           sources=['{component}/in-requirements.txt'.format(component=component)],
                           fixed_requirements='fixed-requirements.txt',
                           output_file='{component}/requirements.txt'.format(component=component))
        print("")


@task(root_requirements, component_requirements, default=True)
def requirements(ctx, default=True):
    pass
