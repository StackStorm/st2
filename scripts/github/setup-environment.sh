#!/usr/bin/env bash

# built-in GitHub Actions environment variables
# https://docs.github.com/en/free-pro-team@latest/actions/reference/environment-variables
#
# setting environment variables, so we can use shell logic
# https://docs.github.com/en/free-pro-team@latest/actions/reference/workflow-commands-for-github-actions#setting-an-environment-variable

IS_NIGHTLY_BUILD=$([ "${GITHUB_EVENT_NAME}" = "schedule" ] && echo "yes" || echo "no")
# shellcheck disable=SC2086
echo "IS_NIGHTLY_BUILD=${IS_NIGHTLY_BUILD}" >> ${GITHUB_ENV}

# NOTE: We only enable coverage for master builds and not pull requests
# since it has huge performance overhead (tests are 50% or so slower)
ENABLE_COVERAGE=$([ "${GITHUB_EVENT_NAME}" != "pull_request" ] && [ "${IS_NIGHTLY_BUILD}" = "no" ] && echo "yes" || echo "no")
# shellcheck disable=SC2086
echo "ENABLE_COVERAGE=${ENABLE_COVERAGE}" >> ${GITHUB_ENV}

# Setup the path to the st2 repo in the CI build system
# shellcheck disable=SC2086
echo "ST2_CI_REPO_PATH=${GITHUB_WORKSPACE}" >> ${GITHUB_ENV}
