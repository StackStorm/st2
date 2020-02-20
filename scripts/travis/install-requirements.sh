#!/usr/bin/env bash

if [[ "${TASK}" = *'ci-py3'* ]]; then
    pip install "tox==3.8.6"

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

    # NOTE: We create the environment and install the dependencies first. This
    # means that the subsequent tox build / test command has a stable run time
    # since it doesn't depend on dependencies being installed.
    build_tox_env() {
        tox -e $1 --notest
    }

    if [[ "${TASK}" = *'ci-py3-unit'* ]]; then
        build_tox_env py36-unit
    fi

    if [[ "${TASK}" = *'ci-py3-packs-tests'* ]]; then
        build_tox_env py36-packs
    fi

    if [[ "${TASK}" = *'ci-py3-integration'* ]]; then
        build_tox_env py36-integration
    fi
else
    make requirements
fi
