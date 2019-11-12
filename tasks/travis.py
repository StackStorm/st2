import os
import subprocess

from invoke import run, task


@task
def prepare_integration(ctx):
    # run("sudo -E scripts/travis/prepare-integration.sh")
    subprocess.Popen('sudo -E ./scripts/travis/prepare-integration.sh',
                     env=os.environ.copy(),
                     shell=True)


@task
def setup_mistral(ctx):
    # run("sudo -E scripts/travis/setup-mistral.sh")
    subprocess.Popen('sudo -E ./scripts/travis/setup-mistral.sh',
                     env=os.environ.copy(),
                     shell=True)


@task
def fix_race(ctx):
    # Fix for Travis CI race
    run("pip install \"six==1.12.0\"")


@task
def bust_cache(ctx):
    # Fix for Travis CI caching issue
    if os.environ.get('TRAVIS_EVENT_TYPE'):
        run("pip uninstall --yes \"pytz\" || echo \"pytz not installed\"")
        run("pip uninstall --yes \"python-dateutil\" || echo \"python-dateutil not installed\"")
        run("pip uninstall --yes \"orquesta\" || echo \"orquesta not installed\"")
