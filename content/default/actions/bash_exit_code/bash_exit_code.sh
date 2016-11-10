#!/usr/bin/env bash

# Produce a random exit code value

n=$((RANDOM%256))

echo "Exit code: ${n}"
exit $n
