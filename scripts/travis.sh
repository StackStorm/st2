#!/usr/bin/env bash

if [ -z ${TASK} ]; then
  echo "No task provided"
  exit 2
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
