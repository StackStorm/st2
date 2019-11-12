from __future__ import print_function

import compileall
import fnmatch
import glob
import modulefinder
import os
import re
import sys

from invoke import exceptions, run, task

import generate
import requirements as requirements_tasks


@task(requirements_tasks.requirements)
def requirements(ctx):
    '''
    Update requirements and then make sure no files were changed
    '''
    print("")
    print("============== CHECKING REQUIREMENTS ==============")
    print("")
    # Update requirements and then make sure no files were changed
    # run("git status -- *requirements.txt */*requirements.txt | grep -q \"nothing to commit\"")
    run("git status -- requirements.txt test-requirements.txt */*requirements.txt | grep -q \"nothing to commit\"")
    print("All requirements files up-to-date!")


@task
def logs(ctx):
    '''
    Summarize statistics for ST2 logs
    '''
    print("")
    print("================== LOG WATCHER ====================")
    print("")
    from tools import log_watcher
    log_watcher.main(['tools/log_watcher.py', '10'])


# The original make target also depended upon lint.flake8, but that causes
# an import cycle, so we skip it
@task(requirements, logs, default=True)
def check(ctx):
    pass


@task(requirements_tasks.requirements)
def bandit(ctx):
    print("")
    print("==================== bandit ====================")
    print("")
    for component in list((set(glob.glob("st2*"))
                           | set(glob.glob("contrib/runners/*")))
                          - set(glob.glob("*.egg-info"))
                          - set(['st2tests', 'st2exporter'])):
        run("bandit -r {component} -lll -x build,dist".format(component=component))


@task(requirements_tasks.requirements)
def compile_(ctx):
    print("")
    print("======================= compile ========================")
    print("")
    print("------- Compile all .py files (syntax check test - Python 2) ------")
    compileall.compile_dir(".", rx=re.compile(r"/virtualenv|virtualenv-osx|virtualenv-py3|.tox|.git|.venv-st2devbox"), quiet=True)


@task
def compilepy3(ctx):
    print("")
    print("======================= compile ========================")
    print("")
    print("------- Compile all .py files (syntax check test - Python 3) ------")
    run("python3 -c 'import compileall,re; compileall.compile_dir(\".\", force=True, quiet=1, rx=re.compile(r\"/virtualenv|.tox|.git|.venv-st2devbox|./st2tests/st2tests/fixtures/packs/test\"), workers=8)'", echo=True)


@task(requirements_tasks.requirements)
def python_packages(ctx):
    '''
    Make target which verifies all the components Python packages are valid
    '''
    print("")
    print("================== CHECK PYTHON PACKAGES ====================")
    print("")

    run("make virtualenv-components")
    for component in list(set(glob.glob("st2*")) - set(glob.glob("*.egg-info")) - set(['st2tests', 'st2exporter'])):
        print("===========================================================")
        print("Checking component: {component}".format(component=component))
        print("===========================================================")
        run("virtualenv-components/bin/python {component}/setup.py --version".format(component=component))


@task
def python_packages_nightly(ctx):
    '''
    Make target which verifies all the components Python packages are valid
    NOTE: This is superset of check-python-packages target.
    We run more extensive and slower tests as part of the nightly build to speed up PR builds
    '''
    print("")
    print("================== CHECK PYTHON PACKAGES ====================")
    print("")

    run("make virtualenv-components")
    for component in list(set(glob.glob("st2*")) - set(glob.glob("*.egg-info")) - set(['st2tests', 'st2exporter'])):
        print("===========================================================")
        print("Checking component: {component}".format(component=component))
        print("===========================================================")
        with ctx.cd(component):
            ctx.run("../virtualenv-components/bin/python setup.py --version")
            ctx.run("../virtualenv-components/bin/python setup.py sdist bdist_wheel")
            ctx.run("../virtualenv-components/bin/python setup.py develop --no-deps")
        ctx.run("virtualenv-components/bin/python -c \"import {component}\"".format(component=component))
        ctx.run("rm -rf {component}/dist/; rm -rf {component}/{component}.egg-info".format(component=component))

@task
def st2client_install(ctx):
    print("")
    print("==================== st2client install check ====================")
    print("")

    run("make virtualenv-st2client")

    # COMPONENTS := $(shell ls -a | grep ^st2 | grep -v .egg-info)
    # COMPONENTS_RUNNERS := $(wildcard contrib/runners/*)
    # COMPONENTS_WITH_RUNNERS := $(COMPONENTS) $(COMPONENTS_RUNNERS)
    # COMPONENTS_WITH_RUNNERS_WITHOUT_MISTRAL_RUNNER := $(foreach component,$(filter-out contrib/runners/mistral_v2,$(COMPONENTS_WITH_RUNNERS)),$(component))
    # COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS_WITH_RUNNERS)))

    # Setup PYTHONPATH in bash activate script...
    components = list(set(glob.glob("st2*") + glob.glob("contrib/runners/*")) - set(glob.glob("*.egg-info") + ['contrib/runners/mistral_v2']))
    print(components)
    # We need to add each component path to the PYTHONPATH for st2client
    with open('virtualenv-st2client/bin/activate', 'r') as f:
        lines = f.readlines()

    # Write out each line, except for the lines that we don't want
    with open('virtualenv-st2client/bin/activate', 'w+') as f:
        for line in lines:
            # Skip writing out lines that start with...
            if any([line.startswith('_OLD_PYTHONPATH'),
                    line.startswith('PYTHONPATH='),
                    line.startswith('export PYTHONPATH')]):
                continue
            f.write(line)

        # Now rewrite those lines
        f.write('_OLD_PYTHONPATH=$PYTHONPATH\n')
        f.write('PYTHONPATH={root_dir}:{components}\n'.format(
            root_dir='.',
            components=':'.join(components)))
        f.write('export PYTHONPATH\n')

    ctx.run("touch virtualenv-st2client/bin/activate")
    ctx.run("chmod +x virtualenv-st2client/bin/activate")

    run("virtualenv-st2client/bin/pip install --upgrade \"pip>=9.0,<9.1\"")
    run("virtualenv-st2client/bin/pip install --upgrade \"setuptools==41.0.1\"")
    with ctx.prefix('../virtualenv-st2client/bin/activate'):
        with ctx.cd('st2client'):
            ctx.run("which python", echo=True)
            ctx.run("python setup.py install", echo=True)
        run("st2 --version")
        run("python -c \"import st2client\"")


@task
def st2client_dependencies(ctx):
    finder = modulefinder.ModuleFinder()
    for root, dirnames, filenames in os.walk('st2client/st2client'):
        for filename in fnmatch.filter(filenames, '*.py'):
            # fname = os.path.join(root, filename)
            # finder.run_script(fname)
            # assert 'st2common' not in finder.modules.keys()
            run("grep -qE 'st2common.*import|import.*st2common' {f} && "
                "exit -1 || exit 0".format(f=os.path.join(root, filename)))


@task
def st2common_circular_dependencies(ctx):
    dont_import_modules = ['st2api', 'st2auth', 'st2debug', 'st2exporter', 'st2reactor']
    modstring = '|'.join(dont_import_modules)
    for root, dirnames, filenames in os.walk('st2common/st2common'):
        for filename in fnmatch.filter(filenames, '*.py'):
            # Note: The jinja asyncsupport.py module is a Python 3-only module, because it
            #       contains uses the async keyword, which is a syntax error in Python 2.
            #       Due to this, we cannot simply import it, not can we use ModuleFinder
            #       like we do in st2client_dependencies.
            #       So instead, we just wrap grep.
            run("grep -qE '({mods}).*import|import.*({mods})' {f} && "
                "exit -1 || exit 0".format(mods=modstring, f=os.path.join(root, filename)))


@task
def generated_files(ctx):
    '''
    Verify that all the files which are automatically generated have indeed been re-generated and
    committed
    '''
    print("==================== generated-files-check ====================")

    # 1. Sample config - conf/st2.conf.sample
    run("cp conf/st2.conf.sample /tmp/st2.conf.sample.upstream")
    generate.config(ctx)
    try:
        run("diff conf/st2.conf.sample /tmp/st2.conf.sample.upstream")
    except exceptions.Failure as e:
        print("conf/st2.conf.sample hasn't been re-generated and committed. Please run \"make configgen\" and include and commit the generated file.", file=sys.stderr)
        raise e
    # 2. OpenAPI definition file - st2common/st2common/openapi.yaml (generated from
    # st2common/st2common/openapi.yaml.j2)
    run("cp st2common/st2common/openapi.yaml /tmp/openapi.yaml.upstream")
    generate.api_spec(ctx)
    try:
        run("diff st2common/st2common/openapi.yaml  /tmp/openapi.yaml.upstream")
    except exceptions.Failure as e:
        print("st2common/st2common/openapi.yaml hasn't been re-generated and committed. Please run \"make generate.api-spec\" and include and commit the generated file.", file=sys.stderr)
        raise e

    print("All automatically generated files are up to date.")


@task
def rst(ctx):
    print("")
    print("==================== rst-check ====================")
    print("")
    run("rstcheck --report warning CHANGELOG.rst")
