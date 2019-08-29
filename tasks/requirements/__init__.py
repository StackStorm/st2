import glob
import os

from invoke import call, Collection, exceptions, run, task

import fixate
from .. import git_tasks
import install
from .. import travis


# COMPONENTS := $(shell ls -a | grep ^st2 | grep -v .egg-info)
# COMPONENTS_RUNNERS := $(wildcard contrib/runners/*)
# COMPONENTS_WITH_RUNNERS := $(COMPONENTS) $(COMPONENTS_RUNNERS)
# COMPONENT_SPECIFIC_TESTS := st2tests *.egg-info
# COMPONENTS_TEST := $(foreach component,$(filter-out $(COMPONENT_SPECIFIC_TESTS),$(COMPONENTS_WITH_RUNNERS)),$(component))
@task
def sdist(ctx):
    # Copy over shared dist utils modules which is needed by setup.py
    for component in glob.glob("contrib/runners/*"):
        run("cp -f scripts/dist_utils.py {component}/dist_utils.py".format(component=component))
        try:
            run("scripts/write-headers.sh {component}/dist_utils.py".format(component=component))
        except exceptions.Failure:
            break

    # Copy over CHANGELOG.RST, CONTRIBUTING.RST and LICENSE file to each component directory
    #@for component in $(COMPONENTS_TEST); do\
    #   test -s $$component/README.rst || cp -f README.rst $$component/; \
    #   cp -f CONTRIBUTING.rst $$component/; \
    #   cp -f LICENSE $$component/; \
    #done


@task(pre=[
          sdist,
          install.runners,
      ],
      post=[
          # Generate all requirements to support current CI pipeline.
          fixate.requirements,
          # Fix for Travis CI race
          travis.fix_race,
          # Fix for Travis CI caching issue
          travis.bust_cache,
          # Install requirements
          install.requirements,
          # Install st2common package to load drivers defined in st2common setup.py
          # NOTE: We pass --no-deps to the script so we don't install all the
          # package dependencies which are already installed as part of "requirements"
          # make targets. This speeds up the build
          call(install.st2common_develop, dummy=1),
          # Note: We install prance here and not as part of any component
          # requirements.txt because it has a conflict with our dependency (requires
          # new version of requests) which we cant resolve at this moment
          install.prance,
          # Install st2common to register metrics drivers
          # NOTE: We pass --no-deps to the script so we don't install all the
          # package dependencies which are already installed as part of "requirements"
          # make targets. This speeds up the build
          call(install.st2common_develop, dummy=2),  # Deduplicate call from previous call
          # Some of the tests rely on submodule so we need to make sure submodules are checked out
          git_tasks.submodule.update,
      ],
      default=True)
def requirements(ctx):
    print('')
    print('==================== requirements ====================')
    print('')
    # Make sure we use the latest version of pip, which is 19
    run("pip --version")
    run("pip install --upgrade \"pip>=19.0,<20.0\"")
    run("pip install --upgrade \"virtualenv==16.6.0\"")  # Required for packs.install in dev envs


namespace = Collection()
namespace.add_task(sdist)
namespace.add_task(requirements)
namespace.add_collection(fixate)
namespace.add_collection(install)
