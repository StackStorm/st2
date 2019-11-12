import glob
import os

from invoke import run, task

import check
import generate
import requirements


@task
def api_spec(ctx):
    print("")
    print("================== Lint API spec ====================")
    print("")
    run("st2common/bin/st2-validate-api-spec --config-file conf/st2.dev.conf")


@task
def circle_api_spec(ctx):
    print("")
    print("================== Lint API spec ====================")
    print("")
    try:
        run("st2common/bin/st2-validate-api-spec --config-file conf/st2.dev.conf")
    except Exception as e:
        print("Open API spec lint failed")
        raise e


@task(requirements.install.test_requirements)
def flake8(ctx):
    print("")
    print("================== flake8 ====================")
    print("")
    run("flake8 --config ./lint-configs/python/.flake8 {components}".format(
        components=' '.join(glob.glob("st2*"))))
    run("flake8 --config ./lint-configs/python/.flake8 {runners}".format(
        runners=' '.join(glob.glob("contrib/runners/*"))))
    run("flake8 --config ./lint-configs/python/.flake8 contrib/packs/actions/")
    run("flake8 --config ./lint-configs/python/.flake8 contrib/linux")
    run("flake8 --config ./lint-configs/python/.flake8 contrib/chatops/")
    run("flake8 --config ./lint-configs/python/.flake8 scripts/")
    run("flake8 --config ./lint-configs/python/.flake8 tools/")
    run("flake8 --config ./lint-configs/python/.flake8 pylint_plugins/")


@task
def pylint(ctx):
    print("")
    print("================== pylint ====================")
    print("")
    # Lint st2 components
    for component in list(set(glob.glob("st2*")) - set(glob.glob("*.egg-info")) - set(['st2tests', 'st2exporter'])):
        print("===========================================================")
        print("Running pylint on {component}".format(component=component))
        print("===========================================================")
        run("pylint -j {pylint_concurrency} -E "
            "--rcfile=./lint-configs/python/.pylintrc "
            "--load-plugins=pylint_plugins.api_models "
            "--load-plugins=pylint_plugins.db_models {component}/{component}".format(
                pylint_concurrency=int(os.environ.get('PYLINT_CONCURRENCY', '1')),
                component=component))

    # Lint runner modules and packages
    for component in glob.glob("contrib/runners/*"):
        print("===========================================================")
        print("Running pylint on {component}".format(component=component))
        print("===========================================================")
        run("pylint -j {pylint_concurrency} -E "
            "--rcfile=./lint-configs/python/.pylintrc "
            "--load-plugins=pylint_plugins.api_models "
            "--load-plugins=pylint_plugins.db_models "
            "{component}/*.py".format(
                pylint_concurrency=int(os.environ.get('PYLINT_CONCURRENCY', '1')),
                component=component))

    # Lint Python pack management actions
    run("pylint -j {pylint_concurrency} -E "
        "--rcfile=./lint-configs/python/.pylintrc "
        "--load-plugins=pylint_plugins.api_models "
        "contrib/packs/actions/*.py "
        "contrib/packs/actions/*/*.py".format(pylint_concurrency=int(os.environ.get('PYLINT_CONCURRENCY', '1'))))
    # Lint other packs
    run("pylint -j {pylint_concurrency} -E "
        "--rcfile=./lint-configs/python/.pylintrc "
        "--load-plugins=pylint_plugins.api_models "
        "contrib/linux/*/*.py "
        "contrib/chatops/*/*.py".format(pylint_concurrency=int(os.environ.get('PYLINT_CONCURRENCY', '1'))))
    # Lint Python scripts
    run("pylint -j {pylint_concurrency} -E "
        "--rcfile=./lint-configs/python/.pylintrc "
        "--load-plugins=pylint_plugins.api_models "
        "scripts/*.py "
        "tools/*.py".format(pylint_concurrency=int(os.environ.get('PYLINT_CONCURRENCY', '1'))))
    run("pylint -j {pylint_concurrency} -E "
        "--rcfile=./lint-configs/python/.pylintrc "
        "pylint_plugins/*.py".format(pylint_concurrency=int(os.environ.get('PYLINT_CONCURRENCY', '1'))))


@task(generate.api_spec, flake8, pylint, check.st2client_dependencies,
      check.st2common_circular_dependencies, check.rst, check.st2client_install, default=True)
def lint(ctx):
    pass
