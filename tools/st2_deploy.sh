#!/bin/bash
set -e

if [ -z $1 ]
then
  VER='0.5.1'
else
  VER=$1
fi

RABBIT_PUBLIC_KEY="rabbitmq-signing-key-public.asc"
PACKAGES="st2common st2reactor st2actions st2client st2api st2auth"
PYTHON=`which python`
BUILD="current"
DEBTEST=`lsb_release -a 2> /dev/null | grep Distributor | awk '{print $3}'`
SYSTEMUSER='stanley'
STANCONF="/etc/st2/st2.conf"

if [[ "$DEBTEST" == "Ubuntu" ]]; then
  TYPE="debs"
  PYTHONPACK="/usr/lib/python2.7/dist-packages"
  echo "########## Detected Distro is ${DEBTEST} ##########"
elif [[ -f "/etc/redhat-release" ]]; then
  TYPE="rpms"
  PYTHONPACK="/usr/lib/python2.7/site-packages"
  echo "########## Detected linux distribution is RedHat compatible ##########"
  systemctl stop firewalld
  systemctl disable firewalld
  setenforce permissive
else
  echo "Unknown Operating System"
  exit 2
fi

RELEASE=`curl -sS -k https://ops.stackstorm.net/releases/st2/${VER}/${TYPE}/current/VERSION.txt`

STAN="/home/${SYSTEMUSER}/${TYPE}"
mkdir -p ${STAN}
mkdir -p /var/log/st2

create_user() {

  if [ $(id -u ${SYSTEMUSER} &> /devnull; echo $?) != 0 ]
  then
    echo "########## Creating system user: ${SYSTEMUSER} ##########"
    useradd ${SYSTEMUSER}
    mkdir -p /home/${SYSTEMUSER}/.ssh
    rm -Rf ${STAN}/*
    chmod 0700 /home/${SYSTEMUSER}/.ssh
    mkdir -p /home/${SYSTEMUSER}/${TYPE}
    echo "########## Generating system user ssh keys ##########"
    ssh-keygen -f /home/${SYSTEMUSER}/.ssh/stanley_rsa -P ""
    cat /home/${SYSTEMUSER}/.ssh/stanley_rsa.pub >> /home/${SYSTEMUSER}/.ssh/authorized_keys
    chmod 0600 /home/${SYSTEMUSER}/.ssh/authorized_keys
    chown -R ${SYSTEMUSER}:${SYSTEMUSER} /home/${SYSTEMUSER}
  fi
}

install_pip() {

  echo "########## Installing packages via pip ##########"
  curl -sS -k -o /tmp/requirements.txt https://ops.stackstorm.net/releases/st2/${VER}/requirements.txt
  pip install -U -r /tmp/requirements.txt
}

install_apt(){
  echo "########## Installing packages via apt-get ##########"

  if [ ! $(grep 'rabbitmq' /etc/apt/sources.list &> /dev/null; echo $?) == 0 ]
  then
    # add rabbitmq APT repo
    echo "########## Adding rabbitmq to sources.list ##########"
    echo 'deb http://www.rabbitmq.com/debian/ testing main' >> /etc/apt/sources.list
    # include public key in trusted key list to avoid warnings
    curl -Ss -k -O http://www.rabbitmq.com/${RABBIT_PUBLIC_KEY}
    sudo apt-key add ${RABBIT_PUBLIC_KEY}
    rm ${RABBIT_PUBLIC_KEY}
  fi
  apt-get update
  # Install packages
  aptlist='rabbitmq-server make python-virtualenv python-dev realpath python-pip mongodb mongodb-server gcc git'
  echo "Installing ${aptlist}"
  apt-get install -y ${aptlist}
  setup_rabbitmq
  setup_mongo
  install_pip
}

install_yum() {
  echo "########## Installing packages via yum ##########"
  rpm --import http://www.rabbitmq.com/rabbitmq-signing-key-public.asc 
  curl -sS -k -o /tmp/rabbitmq-server.rpm http://www.rabbitmq.com/releases/rabbitmq-server/v3.3.5/rabbitmq-server-3.3.5-1.noarch.rpm
  yum localinstall -y /tmp/rabbitmq-server.rpm
  yumlist='python-pip python-virtualenv python-devel gcc-c++ git-all mongodb mongodb-server'
  echo "Installing ${yumlist}"
  yum install -y ${yumlist}
  setup_rabbitmq
  setup_mongo
  install_pip
}

setup_rabbitmq() {
  echo "########## Setting up rabbitmq-server ##########"
  # enable rabbitmq-management plugin
  rabbitmq-plugins enable rabbitmq_management
  # Restart rabbitmq
  service rabbitmq-server restart
  # use rabbitmqctl to check status
  rabbitmqctl status
  # rabbitmaadmin is useful to inspect exchanges, queues etc.
  curl -sS -o /usr/bin/rabbitmqadmin http://localhost:15672/cli/rabbitmqadmin
  chmod 755 /usr/bin/rabbitmqadmin
}

setup_mongo() {
  if [[ "$TYPE" == "debs" ]]; then
    MONGO="mongodb"
  elif [[ "$TYPE" == "rpms" ]]; then
    MONGO="mongod"
  fi
  echo "########## Setting up MongoDB ##########"
  if [ ! $(grep 'replSet' /etc/mongodb.conf &> /dev/null; echo $?) == 0 ]
  then
    echo "replSet = rs0" >> /etc/mongodb.conf
    echo "oplogSize = 100" >> /etc/mongodb.conf
  fi
  sleep 10
  # Make mongodb start now
  service ${MONGO} restart
  # Add hostname to /etc/hosts
  echo -e '127.0.0.1'\\t`hostname` >> /etc/hosts
  # Wait for mongo to spin up
  sleep 10
  # Initiate replication set
  mongo --eval "rs.initiate()"
}

download_pkgs() {
  echo "########## Downloading ${TYPE} packages ##########"
  echo "ST2 Packages: ${PACKAGES}"
  pushd ${STAN}
  for pkg in ${PACKAGES}
  do
    if [[ "$TYPE" == "debs" ]]; then
      PACKAGE="${pkg}_${VER}-${RELEASE}_amd64.deb"
    elif [[ "$TYPE" == "rpms" ]]; then
      PACKAGE="${pkg}-${VER}-${RELEASE}.noarch.rpm"
    fi
    curl -sS -k -O https://ops.stackstorm.net/releases/st2/${VER}/${TYPE}/${BUILD}/${PACKAGE}
  done
  popd
}

deploy_rpm() {
  echo "########## Removing any current st2 components ##########"
  for i in `rpm -qa | grep st2 | grep -v common`; do rpm -e $i; done
  for i in `rpm -qa | grep st2common `; do rpm -e $i; done

  echo "########## Installing st2 ${STAN} ##########"
  pushd ${STAN}
  yum localinstall -y *.rpm
  popd
}

deploy_deb() {
  pushd ${STAN}
  for PACKAGE in $PACKAGES; do
    echo "########## Removing ${PACKAGE} ##########"
    dpkg --purge $PACKAGE
    echo "########## Installing ${PACKAGE} ${VER} ##########"
    dpkg -i ${PACKAGE}*
  done
  popd
}

register_content() {
  echo "########## Registering all content ##########"
  $PYTHON ${PYTHONPACK}/st2common/bin/registercontent.py --config-file ${STANCONF} 
}

create_user
download_pkgs

if [[ "$TYPE" == "debs" ]]; then
  install_apt
  deploy_deb
elif [[ "$TYPE" == "rpms" ]]; then
  install_yum
  deploy_rpm
fi

echo "########## Downloading st2ctl ##########"
curl -sS -k -o /usr/bin/st2ctl https://ops.stackstorm.net/releases/st2/scripts/st2ctl
chmod +x /usr/bin/st2ctl

register_content
echo "########## Starting St2 Services ##########"
st2ctl restart 
sleep 20 
st2 run local date -a

echo "=============================="
echo ""

if [ ! "$?" == 0 ]
then
  echo "ERROR!" 
  echo "Something went wrong, st2 failed to start"
  exit 2
else
  echo "      _   ___     ____  _  __ "
  echo "     | | |__ \   / __ \| |/ / "
  echo "  ___| |_   ) | | |  | | ' /  "
  echo " / __| __| / /  | |  | |  <   "
  echo " \__ \ |_ / /_  | |__| | . \  "
  echo " |___/\__|____|  \____/|_|\_\ "
  echo ""
  echo "  st2 is installed and ready  "
fi
