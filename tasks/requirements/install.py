import glob
import os

from invoke import Collection, run, task


@task
def test_requirements(ctx):
    run("pip install {pip_options} -r test-requirements.txt".format(
        pip_options=os.environ.get('ST2_PIP_OPTIONS', '')), echo=True)


@task
def root_requirements(ctx):
    run("pip install {pip_options} -r requirements.txt".format(
        pip_options=os.environ.get('ST2_PIP_OPTIONS', '')), echo=True)


@task
def fixed_requirements(ctx):
    run("pip install {pip_options} -r fixed-requirements.txt".format(
        pip_options=os.environ.get('ST2_PIP_OPTIONS', '')), echo=True)


@task(test_requirements, root_requirements, fixed_requirements, default=True)
def requirements(ctx):
    pass


# dummy_kwargs is used to deduplicate executions of this task - it is not used
# in any way
@task
def st2common_develop(ctx, **dummy_kwargs):
    # Install st2common package to load drivers defined in st2common setup.py,
    # and also to register metrics drivers
    # NOTE: We pass --no-deps to the script so we don't install all the
    # package dependencies which are already installed as part of "requirements"
    # make targets. This speeds up the build
    with ctx.cd('st2common'):
        ctx.run("python setup.py develop --no-deps")


@task
def flake8(ctx):
    # Manually install flake8
    run("pip install flake8")


@task
def prance(ctx):
    # Note: We install prance here and not as part of any component
    # requirements.txt because it has a conflict with our dependency (requires
    # new version of requests) which we cant resolve at this moment
    run("pip install \"prance==0.15.0\"")


@task
# NOTE: We pass --no-deps to the script so we don't install all the
# package dependencies which are already installed as part of "requirements"
# make targets. This speeds up the build
def runners(ctx):
    print("")
    print("================== INSTALL RUNNERS ====================")
    print("")
    for component in glob.glob("contrib/runners/*"):
        print("===========================================================")
        print("Installing runner: {component}".format(component=component))
        print("===========================================================")
        with ctx.cd(component):
            ctx.run("python setup.py develop --no-deps")
    print("============== DONE INSTALLING RUNNERS ================")
