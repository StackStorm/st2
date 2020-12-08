#!/usr/bin/env bash

set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

mkdir -p /home/runner/.ssh

# Generate ssh keys on StackStorm box and copy over public key into remote box.
ssh-keygen -f /home/runner/.ssh/github_actions_rsa -P ""

# Authorize key-base acces
sh -c 'cat /home/runner/.ssh/github_actions_rsa.pub >> /home/runner/.ssh/authorized_keys'
chmod 0600 /home/runner/.ssh/authorized_keys
chmod 0700 /home/runner/.ssh
chown -R runner:runner /home/runner/.ssh
