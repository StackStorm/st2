#!/usr/bin/env bash

set -e
mkdir -p ~/.ssh

# Generate ssh keys on StackStorm box and copy over public key into remote box.
ssh-keygen -f ~/.ssh/st2_id_rsa -P ""

# Authorize key-base acces
sudo bash -c "cat ~/.ssh/st2_id_rsa.pub >> ~/.ssh/authorized_keys"
sudo chmod 0600 ~/.ssh/authorized_keys
sudo chmod 0700 ~/.ssh
sudo chown -R "${ST2_CI_USER}:${ST2_CI_USER}" ~/.ssh
