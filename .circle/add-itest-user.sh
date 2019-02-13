#!/usr/bin/env bash

set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

UBUNTU_VERSION=`lsb_release -a 2>&1 | grep Codename | grep -v "LSB" | awk '{print $2}'`

# Use "travis" user on Travis CI to avoid permission issue on Ubuntu Xenial
if [ "${TRAVIS}" = "true" ]; then
    USER="travis"
else
    USER="stanley"
fi

# Create an SSH system user (default `stanley` user may be already created)
if (! id ${USER} 2>/dev/null); then
  useradd ${USER}
fi

mkdir -p /home/${USER}/.ssh

# Generate ssh keys on StackStorm box and copy over public key into remote box.
ssh-keygen -f /home/${USER}/.ssh/${USER}_rsa -P ""

# Authorize key-base acces
sh -c "cat /home/${USER}/.ssh/${USER}_rsa.pub >> /home/${USER}/.ssh/authorized_keys"
chmod 0600 /home/${USER}/.ssh/authorized_keys
chmod 0700 /home/${USER}/.ssh
chown -R ${USER}:${USER} /home/${USER}

# Apply sudo fix for local 'circleci' user
sh -c 'echo "circleci    ALL=(ALL)       NOPASSWD: SETENV: ALL" >> /etc/sudoers.d/st2'
# Enable passwordless sudo for 'stanley' user
sh -c 'echo "stanley    ALL=(ALL)       NOPASSWD: SETENV: ALL" >> /etc/sudoers.d/st2'
chmod 0440 /etc/sudoers.d/st2
