#!/usr/bin/env bash

HOST=$1
MAX_HOPS=$2
MAX_QUERIES_TO_HOP=$3

MAX_HOPS="${MAX_HOPS:-30}"
MAX_QUERIES_TO_HOP="${MAX_QUERIES_TO_HOP:-3}"

# echo "$HOST"
# echo "$MAX_HOPS"
# echo "$MAX_QUERIES_TO_HOP"

TRACEROUTE=`which traceroute`
if [ $? -ne 0 ]; then
    echo "Unable to find traceroute binary in PATH" >&2
    exit 2
fi

exec ${TRACEROUTE} -q ${MAX_QUERIES_TO_HOP} -m ${MAX_HOPS} ${HOST}
