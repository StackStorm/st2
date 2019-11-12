from __future__ import print_function

import glob
import sys

from invoke import exceptions, run, task


@task
def cli(ctx):
    print("")
    print("=================== Building st2 client ===================")
    print("")
    with ctx.cd('st2client'):
        try:
            ctx.run("python setup.py develop")
        except exceptions.Failure as e:
            print("!!! ERROR: BUILD FAILED !!!\n", file=sys.stderr)


@task
def rpms(ctx):
    print("")
    print("==================== rpm ====================")
    print("")
    run("rm -Rf ~/rpmbuild")
    for component in list(set(glob.glob("st2*")) - set(glob.glob("*.egg-info")) - set(['st2tests', 'st2exporter'])):
        with ctx.cd(component):
            try:
                ctx.run("make rpm")
            except exceptions.Failure as e:
                raise e
                break
    with ctx.cd("st2client"):
        run("make rpm")


@task
def rhel_rpms(ctx):
    print("")
    print("==================== rpm ====================")
    print("")
    run("rm -Rf ~/rpmbuild")
    for component in list(set(glob.glob("st2*")) - set(glob.glob("*.egg-info")) - set(['st2tests', 'st2exporter'])):
        with ctx.cd(component):
            try:
                ctx.run("make rhel-rpm")
            except exceptions.Failure as e:
                raise e
                break
    with ctx.cd("st2client"):
        ctx.run("make rhel-rpm")


@task
def debs(ctx):
    print("")
    print("==================== deb ====================")
    print("")
    run("rm -Rf ~/debbuild")
    for component in list(set(glob.glob("st2*")) - set(glob.glob("*.egg-info")) - set(['st2tests', 'st2exporter'])):
        with ctx.cd(component):
            try:
                ctx.run("make deb")
            except exceptions.Failure as e:
                raise e
                break
    with ctx.cd('st2client'):
        ctx.run("make deb")
