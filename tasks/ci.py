import glob

from invoke import exceptions, run, task

import check
import lint
import test


@task
def py3_unit(ctx):
    print("")
    print("==================== ci-py3-unit ====================")
    print("")
    run("NOSE_WITH_TIMER=1 tox -e py36-unit -vv")
    run("NOSE_WITH_TIMER=1 tox -e py36-packs -vv")


@task
def py3_unit_nightly(ctx):
    print("")
    print("==================== ci-py3-unit ====================")
    print("")
    run("NOSE_WITH_TIMER=1 tox -e py36-unit-nightly -vv")


@task
def prepare_integration(ctx):
    run("sudo -E scripts/travis/prepare-integration.sh")


@task(prepare_integration)
def py3_integration(ctx):
    print("")
    print("==================== ci-py3-integration ====================")
    print("")
    run("NOSE_WITH_TIMER=1 tox -e py36-integration -vv")


@task(check.compile_, check.generated_files, lint.pylint, lint.flake8, check.requirements,
      check.st2client_dependencies, check.st2common_circular_dependencies, lint.circle_api_spec,
      check.rst, check.st2client_install, check.python_packages)
def checks(ctx):
    pass


@task(checks, test.unit, test.integration, test.mistral, test.packs, default=True)
def ci(ctx, coverage=False, nose_opts=None):
    if coverage:
        run("coverage combine")
        run("coverage report")


@task(check.python_packages_nightly)
def checks_nightly(ctx):
    pass


@task(test.unit)
def unit(ctx, coverage=False, nose_opts=None):
    pass


@task
def unit_nightly(ctx, coverage=False, nose_opts=None):
    # NOTE: We run mistral runner checks only as part of a nightly build to speed up
    # non nightly builds (Mistral will be deprecated in the future)
    print("")
    print("============== ci-unit-nightly ==============")
    print("")

    opts = {
        'rednose': True,
        'immediate': True,
        'with-parallel': True,
    }

    if coverage:
        components = list(set(glob.glob("st2*")) - set(['st2tests']) - set(glob.glob('*.egg-info'))) + ['contrib/runners/mistral_v2']
        opts['with-coverage'] = True
        opts['cover-branches'] = True
        opts['cover-package'] = ','.join(components)

    if nose_opts:
        opts.update(nose_opts)

    opts_list = [
        '--{key}'.format(key=key) if value is True else '--{key}={value}'.format(key=key, value=value)
        for key, value in opts.items()
    ]

    run("nosetests {opts} -s -v contrib/runners/mistral_v2/tests/unit".format(opts=' '.join(opts_list)))


@task(prepare_integration, test.integration)
def integration(ctx, coverage=False, nose_opts=None):
    pass


@task(prepare_integration, test.runners_integration)
def runners(ctx, coverage=False, nose_opts=None):
    pass


@task
def prepare_mistral(ctx):
    run("sudo -E ./scripts/travis/setup-mistral.sh")


@task(prepare_integration, prepare_mistral, test.mistral)
def mistral(ctx, coverage=False, nose_opts=None):
    pass


@task(prepare_integration, test.orquesta)
def orquesta(ctx, coverage=False, nose_opts=None):
    pass


@task(test.packs)
def packs_tests(ctx):
    pass
