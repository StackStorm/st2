#!/usr/bin/env bash
# Copyright 2021 The StackStorm Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script allows users to easily run unit tests in parallel on multi-core systems. Compared
# to just running single-threaded make .unit-tests, this offers much faster run time.

NUM_WORKERS=${NUM_WORKERS:-$(nproc)}

# TODO: Add support for FAIL_ON_FAILURE (aka fail and exit immediately + kill other running
# processes on first failure)

# Needed, otherwise some CLI tests will fail
export COLUMNS=120

echo ""
echo "Running unit tests in parallel"
echo "Using ${NUM_WORKERS} worker(s)"
echo ""

mkdir -p test_logs/
rm test_logs/*

START_TS=$(date +%s)

for (( i=0; i < ${NUM_WORKERS}; i++ ));
do
    WORKER_LOG_PATH="test_logs/worker_${i}_tests.log"
    echo "Spawning worker ${i}, output will be saved to ${WORKER_LOG_PATH}"

    # Spawn worker process in background
    TEMP_DIR=$(mktemp -d -t worker-${i}-XXXXXXXXXX)
    mkdir -p ${TEMP_DIR}/home
    DB_PER_WORKER=1 NODE_TOTAL=${NUM_WORKERS} NODE_INDEX=${i} HOME=${TEMP_DIR}/home make play .unit-tests &> ${WORKER_LOG_PATH} &
    WORKER_PID=$!

    sleep 0.3

    # Tail logs and wait for pid
    tail --pid=${WORKER_PID} -f ${WORKER_LOG_PATH} &
done

FAILURE_COUNTER=0

for job_pid in $(jobs -p); do
    wait ${job_pid} || let "FAILURE_COUNTER+=1"
done

END_TS=$(date +%s)

DURATION=$((END_TS - START_TS))

echo ""
echo "Total duration: ${DURATION} seconds"
echo ""

if [ "${FAILURE_COUNTER}" -gt 0 ]; then
    grep -ri "\\[error\']" test_logs/*.log
    printf "\u274c "
    echo "One or more tests failed, please inspect the output above or logs in test_logs/"
    exit 1
fi

printf '\033[0;32m\u2714 \033[0m'
echo "All tests successfuly passed!"

exit 0
