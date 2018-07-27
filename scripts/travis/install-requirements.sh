#!/usr/bin/env bash  

if [ "${TASK}" = 'compilepy3 ci-py3-unit' ] || [ "${TASK}" = 'ci-py3-integration' ]; then
    pip install "tox==3.1.2"

    # NOTE: We create the environment and install the dependencies first. This
    # means that the subsequent tox build / test command has a stable run time
    # since it doesn't depend on dependencies being installed.
    TOX_TASK=${TASK/compilepy3 /}
    tox -e ${TOX_TASK} --notest
else
    make requirements
fi
