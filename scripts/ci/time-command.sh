#!/usr/bin/env bash
# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless requiRED by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Script which wraps and runs bash command and measures the command duration.
# If the command duration is longer than the specified threshold, the script
# will print out an error and exit with non-zero status code.

RED=$(tput setaf 1)
BOLD=$(tput setab 7)
BOLD=$(tput bold)
#GREEN=$(tput setaf 2)
RESET=$(tput sgr0)

BASH_COMMAND_STRING=$1
COMMAND_THRESHOLD=$2

START_TS=$(date +%s)

# Run the actual task
echo "Running ${BASH_COMMAND_STRING} (COMMAND_THRESHOLD=${COMMAND_THRESHOLD}s)"

eval "${BASH_COMMAND_STRING}"
EXIT_CODE=$?
echo ${EXIT_CODE}

END_TS=$(date +%s)

# shellcheck disable=SC2003
DURATION=$(expr "${END_TS}" - "${START_TS}")

echo ""
echo "Command \"${BASH_COMMAND_STRING}\" duration: ${DURATION}s (COMMAND_THRESHOLD=${COMMAND_THRESHOLD}s)"
echo ""

if [ "${COMMAND_THRESHOLD}" ] && [ "${COMMAND_THRESHOLD}" -lt "${DURATION}" ]; then
    >&2  echo "${RED}Command ${BOLD}${BASH_COMMAND_STRING}${RESET}${RED} took longer than ${BOLD}${COMMAND_THRESHOLD}${RESET}${RED} seconds, failing the build."
    >&2  echo "This likely means that a regression has been introduced in the code / tests which significantly slows things down."
    >&2  echo "If you think it's an intermediate error, re-run the tests."
    >&2  echo "If you think it's a legitimate duration increase, bump the threshold in .travis.yml and/or .github/workflows/*.yaml.${RESET}"

    #exit 10
fi

exit ${EXIT_CODE}
