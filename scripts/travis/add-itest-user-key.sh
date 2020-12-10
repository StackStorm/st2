#!/usr/bin/env bash

set -e
mkdir -p ~/.ssh

# Generate ssh keys on StackStorm box and copy over public key into remote box.
ssh-keygen -f ~/.ssh/github_actions_rsa -P ""

# Authorize key-base acces
sh -c 'cat ~/.ssh/github_actions_rsa.pub >> ~/.ssh/authorized_keys'
chmod 0600 ~/.ssh/authorized_keys
chmod 0700 ~/.ssh
chown -R "${ST2_CI_USER}:${ST2_CI_USER}" ~/.ssh
