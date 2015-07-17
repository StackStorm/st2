#!/usr/bin/env bash
set -e

if [ -z ${TASK} ]; then
  echo "No task provided"
  exit 2
fi

if [ ${TASK} == 'checks' ]; then
  make .flake8
  make .pylint
  make .docs
elif [ ${TASK} == 'unit' ]; then
  # compile .py files, useful as compatibility syntax check
  make compile
  make unit-tests-coverage-xml
else
  echo "Invalid task: ${TASK}"
  exit 2
fi
