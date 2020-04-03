#!/usr/bin/env bash

set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

mkdir -p /home/travis/.ssh

# Generate ssh keys on StackStorm box and copy over public key into remote box.
ssh-keygen -f /home/travis/.ssh/travis_rsa -P ""

# Authorize key-base acces
sh -c 'cat /home/travis/.ssh/travis_rsa.pub >> /home/travis/.ssh/authorized_keys'
chmod 0600 /home/travis/.ssh/authorized_keys
chmod 0700 /home/travis/.ssh
