#!/usr/bin/env bash  

if [ "${TASK}" = 'compilepy3 ci-py3-unit' ] || [ "${TASK}" = 'ci-py3-integration' ]; then
    pip install "tox==3.5.2"

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
    if [ "${TASK}" = 'compilepy3 ci-py3-unit' ]; then
        TOX_TASK="py36-unit"
    fi

    if [ "${TASK}" = 'ci-py3-integration' ]; then
        TOX_TASK="py36-integration"
    fi

    tox -e ${TOX_TASK} --notest
else
    make requirements
fi
