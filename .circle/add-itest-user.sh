#!/usr/bin/env bash

set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

UBUNTU_VERSION=`lsb_release -a 2>&1 | grep Codename | grep -v "LSB" | awk '{print $2}'`

# Create an SSH system user (default `stanley` user may be already created)
if (! id stanley 2>/dev/null); then
  useradd stanley
fi

mkdir -p /home/stanley/.ssh

# Generate ssh keys on StackStorm box and copy over public key into remote box.
ssh-keygen -f /home/stanley/.ssh/stanley_rsa -P ""

# Authorize key-base acces
sh -c 'cat /home/stanley/.ssh/stanley_rsa.pub >> /home/stanley/.ssh/authorized_keys'
chmod 0600 /home/stanley/.ssh/authorized_keys
chmod 0700 /home/stanley/.ssh
chown -R stanley:stanley /home/stanley

# Apply sudo fix for local 'circleci' user
sh -c 'echo "circleci    ALL=(ALL)       NOPASSWD: SETENV: ALL" >> /etc/sudoers.d/st2'
# Enable passwordless sudo for 'stanley' user
sh -c 'echo "stanley    ALL=(ALL)       NOPASSWD: SETENV: ALL" >> /etc/sudoers.d/st2'
chmod 0440 /etc/sudoers.d/st2

# Workaround for Travis on Ubuntu Xenial so local runner integration tests work
# when executing them under user "stanley" (by default Travis checks out the
# code and runs tests under a different system user).
# NOTE: We need to pass "--exe" flag to nosetests when using this workaround.
if [ "${TRAVIS}" = "true" ] && [ "${UBUNTU_VERSION}" == "xenial" ]; then
  echo "Applying workaround for stanley user permissions issue to /home/travis on Xenial"
  chmod 777 -R /home/travis
fi
