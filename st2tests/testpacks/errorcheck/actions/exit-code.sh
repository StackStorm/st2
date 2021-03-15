#!/bin/bash

exit_code=1
if [ -n "$1" ]
    then
        exit_code=$1
fi

exit $exit_code
