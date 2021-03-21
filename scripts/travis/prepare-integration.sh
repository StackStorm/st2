#!/usr/bin/env bash
set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

# Activate the virtualenv created during make requirements phase
source ./virtualenv/bin/activate

# install st2 client
python ./st2client/setup.py develop
st2 --version

# Clean up old screen log files
rm -f logs/screen-*.log

# ::group::/::endgroup:: is helpful github actions syntax to fold this section.
echo ::group::launchdev.sh start -x

# start dev environment in screens
./tools/launchdev.sh start -x

# Give processes some time to start and check logs to see if all the services
# started or if there was any error / failure
echo "Giving screen processes some time to start..."
sleep 10

echo " === START: Catting screen process log files. ==="
cat logs/screen-*.log
echo " === END: Catting screen process log files. ==="

# github actions: fold for launchdev.sh start -x
echo ::endgroup::

# Setup the virtualenv for the examples pack which is required for orquesta integration tests.
st2 run packs.setup_virtualenv packs=examples

# This script runs as root on Travis/GitHub Actions which means other processes which don't run
# as root can't write to logs/ directory and tests fail
chmod 777 logs/
chmod 777 logs/*

# root needs to access write some lock files when creating virtualenvs
# o=other; X=only set execute bit if user execute bit is set (eg on dirs)
chmod -R o+rwX ./virtualenv/
