#!/usr/bin/env bash
set -e

if [ -z ${TASK} ]; then
  echo "No task provided"
  exit 2
fi

if [ ${TASK} == 'checks' ]; then
  # compile .py files, useful as compatibility syntax check
  make compile
  make pylint flake8 docs
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
