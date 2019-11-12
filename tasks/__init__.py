import os

from invoke import Collection, task, run

import build
import check as check_tasks
import ci as ci_tasks
import clean as clean_tasks
import generate
import git_tasks
import lint as lint_tasks
import requirements as requirements_tasks
import test



# All tasks are implemented in submodules of this package
# All tasks in this module are only for reverse compatibility with the original
# Makefile

# This task aliases a Python built-in
@task(requirements_tasks.requirements, generate.config, check_tasks.check, test.pytests)
def all_(ctx):
    pass


@task
def play(ctx):
    '''
    Print out environment variables used by invoke
    '''
    # Since invoke tasks can accept arguments, this isn't as necessary as it
    # was in the Makefile. However, we still use it in Travis tests, so we
    # replicate it here as well, but we only print out environment variables
    # that we use. Most environment variables used in the Makefile.
    print('TRAVIS_PULL_REQUEST: {}'.format(os.environ.get('TRAVIS_PULL_REQUEST')))
    print('')
    print('TRAVIS_EVENT_TYPE: {}'.format(os.environ.get('TRAVIS_EVENT_TYPE')))
    print('')
    print('NOSE_OPTS: {}'.format(os.environ.get('NOSE_OPTS')))
    print('')
    print('NOSE_COVERAGE_FLAGS: {}'.format(os.environ.get('NOSE_COVERAGE_FLAGS')))
    print('')
    print('NOSE_COVERAGE_PACKAGES: {}'.format(os.environ.get('NOSE_COVERAGE_PACKAGES')))
    print('')
    print('ST2_PIP_OPTIONS: {}'.format(os.environ.get('ST2_PIP_OPTIONS')))
    print('')
    print('PYLINT_CONCURRENCY: {}'.format(os.environ.get('PYLINT_CONCURRENCY'), '1'))
    print('')


@task(check_tasks.check)
def check(ctx):
    pass


@task(requirements_tasks.install.runners)
def install_runners(ctx):
    pass


@task(check_tasks.requirements)
def check_requirements(ctx):
    pass


@task(check_tasks.python_packages)
def check_python_packages(ctx):
    pass


@task(check_tasks.python_packages_nightly)
def check_python_packages_nightly(ctx):
    pass


@task(ci_tasks.checks_nightly)
def ci_checks_nightly(ctx):
    pass


@task(check_tasks.logs)
def checklogs(ctx):
    pass


@task(generate.config,  aliases=('.configgen',))
def configgen(ctx):
    pass


@task(lint_tasks.pylint, aliases=('.pylint',))
def pylint(ctx):
    pass


@task(lint_tasks.api_spec, aliases=('.lint_api_spec',))
def lint_api_spec(ctx):
    pass


@task(generate.api_spec, aliases=('.generate_api_spec',))
def generate_api_spec(ctx):
    pass


@task(lint_tasks.circle_api_spec)
def circle_lint_api_spec(ctx):
    pass


@task(lint_tasks.flake8, aliases=('.flake8',))
def flake8(ctx):
    pass


@task(lint_tasks.lint, aliases=('.lint',))
def lint(ctx):
    pass


@task(check_tasks.st2client_install, aliases=('.st2client_install_check',))
def st2client_install_check(ctx):
    pass


@task(check_tasks.bandit, aliases=('.bandit',))
def bandit(ctx):
    pass


@task(clean_tasks.pycs, aliases=('.cleanpycs',))
def cleanpycs(ctx):
    pass


@task(clean_tasks.clean)
def clean(ctx):
    pass


@task(check_tasks.compile_)
def compile_(ctx):
    pass


@task(check_tasks.compilepy3)
def compilepy3(ctx):
    pass


@task(check_tasks.st2client_dependencies, aliases=('.st2client_dependencies_check',))
def st2client_dependencies_check(ctx):
    pass


@task(check_tasks.st2common_circular_dependencies, aliases=('.st2common_circular_dependencies_check',))
def st2common_circular_dependencies(ctx):
    pass


@task(clean_tasks.mongodb, aliases=('.cleanmongodb',))
def cleanmongodb(ctx):
    pass


@task(clean_tasks.mysql, aliases=('.cleanmysql',))
def cleanmysql(ctx):
    pass


@task(clean_tasks.rabbitmq, aliases=('.cleanrabbitmq',))
def cleanrabbitmq(ctx):
    pass


@task(clean_tasks.coverage, aliases=('.cleancoverage',))
def cleancoverage(ctx):
    pass


@task(requirements_tasks.requirements)
def requirements(ctx):
    pass


@task(test.pytests, aliases=('.pytests',))
def pytests(ctx):
    pass


@task(test.pytests)
def tests(ctx):
    pass


@task(test.unit, aliases=('.unit_tests',))
def unit_tests(ctx, coverage=False, nose_opts=None):
    pass


@task(test.integration, aliases=('itests', '.itests',))
def integration_tests(ctx, coverage=False, nose_opts=None):
    pass


@task(test.mistral, aliases=('.mistral-itests',))
def mistral_itests(ctx, coverage=False, nose_opts=None):
    pass


@task(test.orquesta, aliases=('.orquesta-itests',))
def orquesta_itests(ctx, coverage=False, nose_opts=None):
    pass


@task(test.packs, aliases=('.packs-tests',))
def packs_tests(ctx, coverage=False, nose_opts=None):
    pass


@task(test.runners_unit, aliases=('.runners-tests',))
def runners_tests(ctx, coverage=False, nose_opts=None):
    pass


@task(test.runners_integration, aliases=('.runners-itests',))
def runners_itests(ctx, coverage=False, nose_opts=None):
    pass


@task(build.cli)
def cli(ctx):
    pass


@task(build.rpms)
def rpms(ctx):
    pass


@task(build.rhel_rpms)
def rhel_rpms(ctx):
    pass


@task(build.debs)
def debs(ctx):
    pass


@task(requirements_tasks.sdist, aliases=('.sdist-requirements',))
def sdist_requirements(ctx):
    pass


@task(ci_tasks.ci)
def ci(ctx):
    pass


@task(ci_tasks.checks)
def ci_checks(ctx):
    pass


@task(ci_tasks.py3_unit)
def ci_py3_unit(ctx):
    pass


@task(ci_tasks.py3_unit_nightly)
def ci_py3_unit_nightly(ctx):
    pass


@task(ci_tasks.py3_integration, aliases=('.ci_py3_integration',))
def ci_py3_integration(ctx):
    pass


@task(check_tasks.rst, aliases=('.rst_check',))
def rst_check(ctx):
    pass


@task(check_tasks.generated_files, aliases=('.generated_files_check',))
def generated_files_check(ctx):
    pass


@task(ci_tasks.unit)
def ci_unit(ctx):
    pass


@task(ci_tasks.unit_nightly)
def ci_unit_nightly(ctx, coverage=False, nose_opts=None):
    pass


@task(ci_tasks.prepare_integration, aliases=('.ci_prepare_integration',))
def ci_prepare_integration(ctx, coverage=False, nose_opts=None):
    pass


@task(ci_tasks.integration)
def ci_integration(ctx, coverage=False, nose_opts=None):
    pass


@task(ci_tasks.runners)
def ci_runners(ctx, coverage=False, nose_opts=None):
    pass


@task(ci_tasks.prepare_mistral, aliases=('.ci-prepare-mistral',))
def ci_prepare_mistral(ctx):
    pass


@task(ci_tasks.mistral)
def ci_mistral(ctx, coverage=False, nose_opts=None):
    pass


@task(ci_tasks.orquesta)
def ci_orquesta(ctx, coverage=False, nose_opts=None):
    pass


@task(ci_tasks.packs_tests)
def ci_packs_tests(ctx):
    pass


namespace = Collection()

namespace.add_task(all_, name='all')
namespace.add_task(play)
namespace.add_task(check)
namespace.add_task(install_runners)
namespace.add_task(check_requirements)
namespace.add_task(check_python_packages)
namespace.add_task(check_python_packages_nightly)
namespace.add_task(ci_checks_nightly)
namespace.add_task(checklogs)
namespace.add_task(configgen)
namespace.add_task(pylint)
namespace.add_task(lint_api_spec)
namespace.add_task(generate_api_spec)
namespace.add_task(circle_lint_api_spec)
namespace.add_task(flake8)
namespace.add_task(lint)
namespace.add_task(st2client_install_check)
namespace.add_task(bandit)
namespace.add_task(cleanpycs)
namespace.add_task(clean)
namespace.add_task(compile_, name='compile')
namespace.add_task(compilepy3)
namespace.add_task(st2client_dependencies_check)
namespace.add_task(st2common_circular_dependencies)
namespace.add_task(cleanmongodb)
namespace.add_task(cleanmysql)
namespace.add_task(cleanrabbitmq)
namespace.add_task(cleancoverage)
namespace.add_task(requirements)
namespace.add_task(pytests)
namespace.add_task(tests)
namespace.add_task(unit_tests)
namespace.add_task(integration_tests)
namespace.add_task(mistral_itests)
namespace.add_task(orquesta_itests)
namespace.add_task(packs_tests)
namespace.add_task(runners_tests)
namespace.add_task(runners_itests)
namespace.add_task(cli)
namespace.add_task(rpms)
namespace.add_task(rhel_rpms)
namespace.add_task(debs)
namespace.add_task(sdist_requirements)
namespace.add_task(ci)
namespace.add_task(ci_checks)
namespace.add_task(ci_py3_unit)
namespace.add_task(ci_py3_unit_nightly)
namespace.add_task(ci_py3_integration)
namespace.add_task(rst_check)
namespace.add_task(generated_files_check)
namespace.add_task(ci_unit)
namespace.add_task(ci_unit_nightly)
namespace.add_task(ci_prepare_integration)
namespace.add_task(ci_integration)
namespace.add_task(ci_runners)
namespace.add_task(ci_prepare_mistral)
namespace.add_task(ci_mistral)
namespace.add_task(ci_orquesta)
namespace.add_task(ci_packs_tests)

# Once we transition to invoke, we can switch to calling tasks directly
# namespace.add_collection(build)
# namespace.add_collection(check_tasks)
# namespace.add_collection(ci_tasks)
# namespace.add_collection(clean_tasks)
# namespace.add_collection(generate)
# namespace.add_collection(lint_tasks)
# namespace.add_collection(test)
# namespace.add_collection(requirements_tasks, name='requirements')
