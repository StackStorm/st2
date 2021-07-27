#!/usr/bin/env bash

# Print various binary versions
git --version
pip --version
pip list
virtualenv --version
shellcheck --version

# Print out various environment variables info
make play
