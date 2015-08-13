#!/bin/sh

component=$(basename `pwd`)
version=$(cat ../st2common/st2common/__init__.py | grep __version__ | sed -r 's/.*=\s+//')

# If there's no specific version for a component, we should set it.
if (cat $component/__init__.py | grep -vq __version__); then
  echo "__version__ = ${version}" >> $component/__init__.py
fi
