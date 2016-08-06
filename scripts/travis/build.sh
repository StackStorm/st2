#!/usr/bin/env bash
set -e

if [ -z ${TASK} ]; then
  echo "No task provided"
  exit 2
fi

# Note: We add bin directory of the MongoDB installation we use to PATH so
# correct version of Mongo shell is used by makefile, etc.
if [ ! -z ${MONGODB} ]; then
  export PATH=${PWD}/mongodb-linux-x86_64-${MONGODB}/bin/:${PATH}
fi

if [ ${TASK} == 'checks' ]; then
  # compile .py files, useful as compatibility syntax check
  make compile
  make pylint flake8 bandit .st2client-dependencies-check .st2common-circular-dependencies-check
elif [ ${TASK} == 'unit' ]; then
  # compile .py files, useful as compatibility syntax check
  make compile
  make .unit-tests-coverage-html
elif [ ${TASK} == 'integration' ]; then
  make .itests-coverage-html
elif [ ${TASK} == 'mistral' ]; then
  make .mistral-itests-coverage-html
elif [ ${TASK} == "packs-tests" ]; then
  make .packs-tests
else
  echo "Invalid task: ${TASK}"
  exit 2
fi
