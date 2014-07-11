#!/usr/bin/env bash

echo "count>>${count}<<"
if [[ ! $count ]]; then
    # count variable not set so default to 3
    PING_COUNT=3
else
    PING_COUNT=${count}
fi

ping -c ${PING_COUNT} ${1}
