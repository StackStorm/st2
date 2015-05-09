#!/usr/bin/env bash

function version_ge() { test "$(echo "$@" | tr " " "\n" | sort -V | tail -n 1)" == "$1"; }

if [ -z ${TASK} ]; then
  echo "No task provided"
  exit 2
  fi

# Note: We only want to run tests under multiple Python versions

if version_ge ${TRAVIS_PYTHON_VERSION} "2.7" && [ ${TASK} != "tests" ]; then
    echo "Skipping task ${TASK} on ${TRAVIS_PYTHON_VERSION}"
    exit 0
fi

if [ ${TASK} == "flake8" ]; then
  make flake8
elif [ ${TASK} == "pylint" ]; then
  make pylint
elif [ ${TASK} == "docs" ]; then
  make docs
elif [ ${TASK} == "tests" ]; then
  make tests-travis
else
  echo "Invalid task: ${TASK}"
  exit 2
fi

exit $?
