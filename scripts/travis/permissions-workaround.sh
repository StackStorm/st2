#!/usr/bin/env bash

set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

UBUNTU_VERSION=`lsb_release -a 2>&1 | grep Codename | grep -v "LSB" | awk '{print $2}'`

# Workaround for Travis on Ubuntu Xenial so local runner integration tests work
# when executing them under user "stanley" (by default Travis checks out the
# code and runs tests under a different system user).
# NOTE: We need to pass "--exe" flag to nosetests when using this workaround.
if [ "${UBUNTU_VERSION}" == "xenial" ]; then
  echo "Applying workaround for stanley user permissions issue to /home/travis on Xenial"
  chmod 777 -R /home/travis
fi
