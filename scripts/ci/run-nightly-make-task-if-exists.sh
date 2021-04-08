#!/usr/bin/env bash

# Script which runs a corresponding make nightly tasks if it exists. If a task corresponding
# nightly task doesn't exist, it's ignored.
#
# For example, let's say we have TASK="ci-checks ci-unit ci-pack-tests" and only
# "ci-checks-nightly" make task exists.
# In this scenario, only "ci-check-nightly" tasks would run and other would be ignored.

TASK=$1

if [ ! "${TASK}" ]; then
    echo "Missing TASK argument"
    echo "Usage: $0 <make task>"
    exit 2
fi

# Note: TASK could contain a list of multiple tasks
# shellcheck disable=SC2068,SC2206
TASKS=($TASK)

EXISTING_TASKS=()
for TASK_NAME in "${TASKS[@]}"; do
    make -n "${TASK_NAME}-nightly" &> /dev/null

    # shellcheck disable=SC2181
    if [ $? -eq 0 ]; then
        # Task {TASK}-nightly exists
        EXISTING_TASKS+=("$TASK_NAME-nightly")
    fi
done

# Run only tasks which exist
if [ ${#EXISTING_TASKS[@]} -eq 0 ]; then
    echo "No existing nightly tasks found..."
    exit 0
fi

# shellcheck disable=SC2145
echo "Running the following nightly tasks: ${EXISTING_TASKS[@]}"
exec make "${EXISTING_TASKS[@]}"
