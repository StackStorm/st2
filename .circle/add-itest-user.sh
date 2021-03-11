#!/usr/bin/env bash

set -ex

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

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
