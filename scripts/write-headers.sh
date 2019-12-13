#!/bin/bash

HEADER="# NOTE: This file is auto-generated - DO NOT EDIT MANUALLY\\
#       Instead modify scripts/dist_utils.py and run 'make .sdist-requirements' to\\
#       update dist_utils.py files for all components\\
"

if [[ $(uname) == "Linux" ]]; then
	sed -i -e "1s;^;$HEADER;" $* || exit -1
elif [[ $(uname) == "Darwin" ]]; then
	sed -i '' -e "1s;^;$HEADER;" $* || exit -1
else
	echo >&2 "Unknown OS"
	exit -1
fi

