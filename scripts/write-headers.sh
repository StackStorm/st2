#!/bin/bash

# This script adds the $HEADER to the top of the file, and strips out any
# comments in the source file/s that start with '# //'
# It also keeps first line encoding hints, eg:
# -*- coding: utf-8 -*-
# that are used by popular editors and formalized in PEP 263
# https://www.python.org/dev/peps/pep-0263/

HEADER="\\
# NOTE: This file is auto-generated - DO NOT EDIT MANUALLY\\
#       Instead modify scripts/dist_utils.py and run 'make .sdist-requirements' to\\
#       update dist_utils.py files for all components\\
"

if [[ $(uname) == "Linux" ]]; then
	sed -i -e "s|^\(# -\*- .*\)$|\1$HEADER|; /^# \/\//d" "$@" || exit 2
elif [[ $(uname) == "Darwin" ]]; then
	sed -i '' -e "s|^\(# -\*- .*\)$|\1$HEADER|; /^# \/\//d" "$@" || exit 2
else
	echo >&2 "Unknown OS"
	exit 2
fi
