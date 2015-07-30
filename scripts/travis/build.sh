#!/usr/bin/env bash
set -e

if [ -z ${TASK} ]; then
  echo "No task provided"
  exit 2
fi

if [ ${TASK} == 'unit' ]; then
  # compile .py files, useful as compatibility syntax check
  make compile
  make .unit-tests-coverage-html
elif [ ${TASK} == 'integration' ]; then
  make .itests-coverage-html
else
  echo "Invalid task: ${TASK}"
  exit 2
fi
