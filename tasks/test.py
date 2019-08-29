import glob

from invoke import call, exceptions, run, task

import check
import lint
import requirements
import travis


@task
def drop_db(ctx):
    print("----- Dropping st2-test db -----")
    run("mongo st2-test --eval \"db.dropDatabase();\"")


@task(requirements.requirements)
def components(ctx, what='unit', coverage=False, nose_opts=None):
    print("")
    print("==================== {what} tests{with_coverage} ====================".format(
        what=what,
        with_coverage=' with coverage' if coverage else ''))
    print("")

    components = list(set(glob.glob("st2*")) - set(['st2tests']) - set(glob.glob('*.egg-info')))

    opts = {
        'rednose': True,
        'immediate': True,
        'with-parallel': True,
    }

    if coverage:
        opts['with-coverage'] = True
        opts['cover-branches'] = True
        opts['cover-package'] = ','.join(components)

    if nose_opts:
        opts.update(nose_opts)

    opts_list = [
        '--{key}'.format(key=key) if value is True else '--{key}={value}'.format(key=key, value=value)
        for key, value in opts.items()
    ]

    for component in components:
        print("===========================================================")
        print("Running tests in {component}".format(component=component))
        print("-----------------------------------------------------------")
        print("")
        ctx.run("nosetests {opts} -s -v {component}/tests/{what}".format(
            opts=' '.join(opts_list),
            component=component,
            what=what))
        print("")
        print("-----------------------------------------------------------")
        print("Done running tests in {component}".format(component=component))
        print("===========================================================")


@task(pre=[drop_db])
def unit(ctx, coverage=False, nose_opts=None):
    components(ctx, what='unit', coverage=coverage, nose_opts=nose_opts)


@task(pre=[drop_db, travis.prepare_integration])
def integration(ctx, coverage=False, nose_opts=None):
    components(ctx, what='integration', coverage=coverage, nose_opts=nose_opts)


@task(pre=[travis.prepare_integration, travis.setup_mistral])
def mistral(ctx, coverage=False, nose_opts=None):
    print("")
    print("==================== MISTRAL integration tests ====================")
    print("The tests assume both st2 and mistral are running on 127.0.0.1.")
    print("")

    opts = {
        'rednose': True,
        'immediate': True,
        'with-parallel': True,
    }

    if coverage:
        opts['with-coverage'] = True
        opts['cover-branches'] = True
        opts['cover-package'] = ','.join(component + runners)

    if nose_opts:
        opts.update(nose_opts)

    opts_list = [
        '--{key}'.format(key=key) if value is True else '--{key}={value}'.format(key=key, value=value)
        for key, value in opts.items()
    ]

    run("nosetests {opts} -s -v st2tests/integration/mistral".format(opts=' '.join(opts_list)))


@task
def orquesta(ctx, coverage=False, nose_opts=None):
    print("")
    print("==================== Orquesta integration tests ====================")
    print("The tests assume st2 is running on 127.0.0.1.")
    print("")

    opts = {
        'rednose': True,
        'immediate': True,
        'with-parallel': True,
    }

    if coverage:
        opts['with-coverage'] = True
        opts['cover-branches'] = True
        opts['cover-package'] = ','.join(component + runners)

    if nose_opts:
        opts.update(nose_opts)

    opts_list = [
        '--{key}'.format(key=key) if value is True else '--{key}={value}'.format(key=key, value=value)
        for key, value in opts.items()
    ]

    run("nosetests {opts} -s -v st2tests/integration/orquesta".format(opts=' '.join(opts_list)))


@task
def packs(ctx):
    print("")
    print("==================== packs-tests ====================")
    print("")
    # Install st2common to register metrics drivers
    with ctx.cd('st2common'):
        ctx.run("python setup.py develop --no-deps")
    # If the search pattern to glob.glob ends in a slash, it only searches for
    # directories (eg: packs). Otherwise, it also includes README.md, which
    # causes the st2-run-pack-tests command to fail.
    contrib_packs = glob.glob("contrib/*/")
    for pack in contrib_packs:
        run("st2common/bin/st2-run-pack-tests -c -t -x -p {filename}".format(filename=pack))


def runners(ctx, what='unit', coverage=False, nose_opts=None):
    print("")
    print("====================== runners-tests ======================")
    print("")

    opts = {
        'rednose': True,
        'immediate': True,
        'with-parallel': True,
    }

    if coverage:
        opts['with-coverage'] = True
        opts['cover-branches'] = True
        opts['cover-package'] = ','.join(component + runners)

    if nose_opts:
        opts.update(nose_opts)

    opts_list = [
        '--{key}'.format(key=key) if value is True else '--{key}={value}'.format(key=key, value=value)
        for key, value in opts.items()
    ]
    runners = glob.glob("contrib/runners/*")

    for runner in runners:
        print("")
        print("===========================================================")
        print("")
        print("Running tests in {runner}".format(runner=runner))
        print("")
        print("===========================================================")
        run("nosetests {opts} -s -v {runner}/tests/{what}".format(opts=' '.join(opts_list), runner=runner, what=what))


@task(drop_db)
def runners_unit(ctx, coverage=False, nose_opts=None):
    runners(ctx, what='unit', coverage=coverage, nose_opts=nose_opts)


@task(drop_db)
def runners_integration(ctx, coverage=False, nose_opts=None):
    runners(ctx, what='integration', coverage=coverage, nose_opts=nose_opts)


@task
def pytests_coverage(ctx):
    unit(ctx, coverage=True)


@task(check.compile_, lint.flake8, lint.pylint, unit, default=True)
def pytests(ctx):
    pass
