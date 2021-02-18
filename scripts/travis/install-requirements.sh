#!/usr/bin/env bash

# This file gets run for all ci jobs.

# virtualenv prepartion is different for python3, so we want all py3 targets here.
# We use a glob instead of listing TASKs so TASK reorganization doesn't require so many changes.
if [[ " ${TASK}" = *' ci-py3-'* ]]; then
    pip install "tox==3.8.6"

    # NOTE: The makefile only checks to see if the activate script is present.
    # It does not check if the virtualenv was built with the correct python version.
    # Since the makefile defaults to python2.7, a 2.7 virtualenv might get cached.
    # Specifying PYTHON_VERSION in .travis.yml or .github/workflows/*.yml should alleviate that,
    # but we'll check the version here just to be sure a cached virtualenv doesn't
    # silently invalidate the tests.

    # cleanup any invalid python2 cache
    test -d virtualenv/lib/${PYTHON_VERSION} || rm -rf virtualenv/*
    # rebuild virtualenv if necessary
    test -f virtualenv/bin/activate || virtualenv --python=${PYTHON_VERSION} virtualenv --no-download

    # Install runners
    . virtualenv/bin/activate

    CURRENT_DIR=`pwd`
    for RUNNER in `ls -d $CURRENT_DIR/contrib/runners/*`
    do
      echo "Installing runner: $RUNNER..."
      cd $RUNNER
      python setup.py develop --no-deps
    done
    # Install mock runners
    for RUNNER in `ls -d $CURRENT_DIR/st2common/tests/runners/*`
    do
      echo "Installing mock runner: $RUNNER..."
      cd $RUNNER
      python setup.py develop --no-deps
    done

    # NOTE: We create the environment and install the dependencies first. This
    # means that the subsequent tox build / test command has a stable run time
    # since it doesn't depend on dependencies being installed.
    # NOTE: CI jobs can have more than one TASK, so we search for all make
    # targets that need a tox env. The spaces ensure we match entire make targets.
    if [[ " ${TASK} " = *' ci-py3-unit '* ]]; then
        tox -e py36-unit --notest
    fi

    if [[ " ${TASK} " = *' ci-py3-packs-tests '* ]]; then
        tox -e py36-packs --notest
    fi

    if [[ " ${TASK} " = *' ci-py3-integration '* ]]; then
        tox -e py36-integration --notest
    fi
else
    make requirements
fi
