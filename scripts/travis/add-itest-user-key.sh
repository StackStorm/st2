#!/usr/bin/env bash

set -ex
mkdir -p ~/.ssh

# Generate ssh keys on StackStorm box and copy over public key into remote box.
ssh-keygen -f ~/.ssh/st2_id_rsa -P ""

# sudo -E = preserve HOME var
# Authorize key-base acces
sudo -E bash -xc "cat ~/.ssh/st2_id_rsa.pub >> ~/.ssh/authorized_keys"
sudo -E chmod 0600 ~/.ssh/authorized_keys
sudo -E chmod 0700 ~/.ssh
sudo -E chown -R "${ST2_CI_USER}:${ST2_CI_USER}" ~/.ssh
