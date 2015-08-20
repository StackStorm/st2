#!/usr/bin/env bash

HOST=$1
MAX_HOPS=$2
MAX_QUERIES_TO_HOP=$3

MAX_HOPS="${MAX_HOPS:-30}"
MAX_QUERIES_TO_HOP="${MAX_QUERIES_TO_HOP:-3}"

# echo "$HOST"
# echo "$MAX_HOPS"
# echo "$MAX_QUERIES_TO_HOP"

echo `traceroute -q $MAX_QUERIES_TO_HOP -m $MAX_HOPS $HOST`
