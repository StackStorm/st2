#!/usr/bin/env bash
set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

# create and configure user
VIRTUALENV_DIR=virtualenv

create_user() {
  echo "###########################################################################################"
  echo "# Creating system user: stanley"

  if (! id stanley 2>/dev/null); then
    useradd stanley
  fi

  SYSTEM_HOME=$(echo ~stanley)

  mkdir -p ${SYSTEM_HOME}/.ssh

  if ! test -s ${SYSTEM_HOME}/.ssh/stanley_rsa; then
    ssh-keygen -f ${SYSTEM_HOME}/.ssh/stanley_rsa -P ""
  fi

  if ! grep -s -q -f ${SYSTEM_HOME}/.ssh/stanley_rsa.pub ${SYSTEM_HOME}/.ssh/authorized_keys;
  then
    # Authorize key-base access
    cat ${SYSTEM_HOME}/.ssh/stanley_rsa.pub >> ${SYSTEM_HOME}/.ssh/authorized_keys
  fi

  chmod 0600 ${SYSTEM_HOME}/.ssh/authorized_keys
  chmod 0700 ${SYSTEM_HOME}/.ssh
  chown -R stanley:stanley ${SYSTEM_HOME}

  # Enable passwordless sudo
  local STANLEY_SUDOERS="stanley    ALL=(ALL)       NOPASSWD: SETENV: ALL"
  if ! grep -s -q ^"${STANLEY_SUDOERS}" /etc/sudoers.d/st2; then
    echo "${STANLEY_SUDOERS}" >> /etc/sudoers.d/st2
  fi

  chmod 0440 /etc/sudoers.d/st2

  # Disable requiretty for all users
  sed -i -r "s/^Defaults\s+\+?requiretty/# Defaults requiretty/g" /etc/sudoers
}

create_user

# install screen
apt-get install -y screen

# Activate the virtualenv created during make requirements phase
source ./virtualenv/bin/activate

# install st2 client
python ./st2client/setup.py develop
st2 --version

# start dev environment in screens
./tools/launchdev.sh start -x

# This script runs as root on Travis which means other processes which don't run
# as root can't write to logs/ directory and tests fail
chmod 777 logs/
chmod 777 logs/*

# Workaround for Travis on Ubuntu Xenial so local runner integration tests work
# when executing them under user "stanley" (by default Travis checks out the
# code and runs tests under a different system user).
# NOTE: We need to pass "--exe" flag to nosetests when using this workaround.
chmod 777 -R /home/travis
