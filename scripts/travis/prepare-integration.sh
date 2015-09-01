#!/usr/bin/env bash
set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

# create and configure user
# proudly stolen from `./tools/st2_deploy.sh`
TYPE='debs'
SYSTEMUSER='stanley'
STAN="/home/${SYSTEMUSER}/${TYPE}"
mkdir -p ${STAN}

create_user() {
  if [ $(id -u ${SYSTEMUSER} &> /devnull; echo $?) != 0 ]
  then
    echo "###########################################################################################"
    echo "# Creating system user: ${SYSTEMUSER}"
    useradd ${SYSTEMUSER}
    mkdir -p /home/${SYSTEMUSER}/.ssh
    rm -Rf ${STAN}/*
    chmod 0700 /home/${SYSTEMUSER}/.ssh
    mkdir -p /home/${SYSTEMUSER}/${TYPE}
    echo "###########################################################################################"
    echo "# Generating system user ssh keys"
    ssh-keygen -f /home/${SYSTEMUSER}/.ssh/stanley_rsa -P ""
    cat /home/${SYSTEMUSER}/.ssh/stanley_rsa.pub >> /home/${SYSTEMUSER}/.ssh/authorized_keys
    chmod 0600 /home/${SYSTEMUSER}/.ssh/authorized_keys
    chown -R ${SYSTEMUSER}:${SYSTEMUSER} /home/${SYSTEMUSER}
    if [ $(grep 'stanley' /etc/sudoers.d/* &> /dev/null; echo $?) != 0 ]
    then
      echo "${SYSTEMUSER}    ALL=(ALL)       NOPASSWD: SETENV: ALL" >> /etc/sudoers.d/st2
      chmod 0440 /etc/sudoers.d/st2
    fi

    # make sure requiretty is disabled.
    sed -i "s/^Defaults\s\+requiretty/# Defaults requiretty/g" /etc/sudoers
  fi
}

create_user

# make sure we are using latest version of pip
pip install --upgrade pip

# install st2 client
python ./st2client/setup.py develop
st2 --version

# install screen
apt-get install -y screen

# start dev environment in screens
./tools/launchdev.sh start
