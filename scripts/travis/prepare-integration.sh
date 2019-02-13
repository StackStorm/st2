#!/usr/bin/env bash
set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

UBUNTU_VERSION=`lsb_release -a 2>&1 | grep Codename | grep -v "LSB" | awk '{print $2}'`

# Activate the virtualenv created during make requirements phase
source ./virtualenv/bin/activate

# install st2 client
python ./st2client/setup.py develop
st2 --version

# start dev environment in screens
./tools/launchdev.sh start -x

# This script runs as root on Travis which means other processes which don't run
# as root can't write to logs/ directory and tests fail
chmod 777 logs/
chmod 777 logs/*
