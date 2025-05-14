#!/usr/bin/env bash

set -ex

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

mkdir -p ~/.ssh

# Generate ssh keys on StackStorm box and copy over public key into remote box.
ssh-keygen -f ~/.ssh/st2_id_rsa -P ""

# Authorize key-base access
cat ~/.ssh/st2_id_rsa.pub >> ~/.ssh/authorized_keys

chmod 0600 ~/.ssh/authorized_keys
chmod 0700 ~/.ssh

chown -R "${ST2_CI_USER}:${ST2_CI_USER}" ~/.ssh

SYSTEM_USER=${ST2TESTS_SYSTEM_USER:-${ST2_SYSTEM_USER__USER:-stanley}}

# Create an SSH system user (default `stanley` user may be already created)
if (! id "${SYSTEM_USER}" 2>/dev/null); then
  useradd "${SYSTEM_USER}"
fi

mkdir -p "/home/${SYSTEM_USER}/.ssh"

# Generate ssh keys on StackStorm box and copy over public key into remote box.
ssh-keygen -f "/home/${SYSTEM_USER}/.ssh/stanley_rsa" -P ""

# Authorize key-base acces
sh -c "cat /home/${SYSTEM_USER}/.ssh/stanley_rsa.pub >> /home/${SYSTEM_USER}/.ssh/authorized_keys"
chmod 0600 "/home/${SYSTEM_USER}/.ssh/authorized_keys"
chmod 0700 "/home/${SYSTEM_USER}/.ssh"
chown -R "${SYSTEM_USER}:${SYSTEM_USER}" "/home/${SYSTEM_USER}"

# Apply sudo fix for GHA runner user
sh -c 'echo "runner ALL=(ALL)       NOPASSWD: SETENV: ALL" >> /etc/sudoers.d/st2'
# Enable passwordless sudo for 'stanley' user
sh -c "echo '${SYSTEM_USER}    ALL=(ALL)       NOPASSWD: SETENV: ALL' >> /etc/sudoers.d/st2"
chmod 0440 /etc/sudoers.d/st2
