#!/usr/bin/env bash

function run_tox()
{
    TOX_TASK="$1"
    pip install "tox==3.8.6"

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
    tox -e ${TOX_TASK} --notest
}

# $TASK is matched from .travis.yml task definitions and maps to tox.ini envlist
case "${TASK}" in
    "compilepy3 ci-py3-unit")
        run_tox "py36-unit"
        ;;
    "ci-py3-integration")
        run_tox "py36-integration"
        ;;
    "compilepy3 ci-py37-unit")
        run_tox "py37-unit"
        ;;
    "ci-py37-integration")
        run_tox "py37-integration"
        ;;
    *)
        make requirements
        ;;
esac

