#!/usr/bin/env bash

# Script which runs make tasks if it exists. If it doesn't exist, it exits with
# 0 status code
TASK=$1

if [ ! "${TASK}" ]; then
    echo "Missing TASK argument"
    exit 2
fi

$(make -n ${TASK} &> /dev/null)

if [ $? -eq 2 ]; then
    # tASK DOESN'T EXIST
    echo "Task ${TASK} doesn't exist, skipping execution..."
    exit 0
fi

exec make ${TASK}
