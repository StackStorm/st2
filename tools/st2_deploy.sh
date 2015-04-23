#!/usr/bin/env bash

# Constants
read -r -d '' WARNING_MSG << EOM
######################################################################
######                       WARNING                           #######
######################################################################

This scripts allows you to evaluate StackStorm on a single server and
is not intended to be used for production deployments.

For more information, see http://docs.stackstorm.com/install/index.html
EOM

WARNING_SLEEP_DELAY=5

# Options which can be provied by the user via env variables
INSTALL_ST2CLIENT=${INSTALL_ST2CLIENT:-1}
INSTALL_WEBUI=${INSTALL_WEBUI:-1}
INSTALL_MISTRAL=${INSTALL_MISTRAL:-1}

# Common variables
DOWNLOAD_SERVER="https://downloads.stackstorm.net"
RABBIT_PUBLIC_KEY="rabbitmq-signing-key-public.asc"
PACKAGES="st2common st2reactor st2actions st2api st2auth st2debug"
CLI_PACKAGE="st2client"
PYTHON=`which python`
BUILD="current"
DEBTEST=`lsb_release -a 2> /dev/null | grep Distributor | awk '{print $3}'`
SYSTEMUSER='stanley'
STANCONF="/etc/st2/st2.conf"

# Information about a test account which used by st2_deploy
TEST_ACCOUNT_USERNAME="testu"
TEST_ACCOUNT_PASSWORD="testp"

# Content for the test htpasswd file used by auth
AUTH_FILE_PATH="/etc/st2/htpasswd"
HTPASSWD_FILE_CONTENT="testu:{SHA}V1t6eZLxnehb7CTBuj61Nq3lIh4="

# WebUI
WEBUI_CONFIG_PATH="/opt/stackstorm/static/webui/config.js"

# Common utility functions
function version_ge() { test "$(echo "$@" | tr " " "\n" | sort -V | tail -n 1)" == "$1"; }
function join { local IFS="$1"; shift; echo "$*"; }

# Distribution specific variables
APT_PACKAGE_LIST=("rabbitmq-server" "make" "python-virtualenv" "python-dev" "realpath" "python-pip" "mongodb" "mongodb-server" "gcc" "git")
YUM_PACKAGE_LIST=("python-pip" "python-virtualenv" "python-devel" "gcc-c++" "git-all" "mongodb" "mongodb-server")

if [ ${INSTALL_MISTRAL} == "1" ]; then
    APT_PACKAGE_LIST+=("mysql-server")
    YUM_PACKAGE_LIST+=("mysql-server")
fi

APT_PACKAGE_LIST=$(join " " ${APT_PACKAGE_LIST[@]})
YUM_PACKAGE_LIST=$(join " " ${YUM_PACKAGE_LIST[@]})

# Actual code starts here

echo "${WARNING_MSG}"
echo ""
echo "To abort press CTRL-C otherwise installation will continue in ${WARNING_SLEEP_DELAY} seconds"
sleep ${WARNING_SLEEP_DELAY}

if [ -z $1 ]
then
  VER='0.8.2'
elif [[ "$1" == "latest" ]]; then
   VER='0.9dev'
else
  VER=$1
fi

echo "Installing version ${VER}"

# Determine which mistral version to use
if version_ge $VER "0.9"; then
    MISTRAL_STABLE_BRANCH="st2-0.9.0"
elif version_ge $VER "0.8.1"; then
    MISTRAL_STABLE_BRANCH="st2-0.8.1"
elif version_ge $VER "0.8"; then
    MISTRAL_STABLE_BRANCH="st2-0.8.0"
else
    MISTRAL_STABLE_BRANCH="st2-0.5.1"
fi

if [[ "$DEBTEST" == "Ubuntu" ]]; then
  TYPE="debs"
  PYTHONPACK="/usr/lib/python2.7/dist-packages"
  echo "###########################################################################################"
  echo "# Detected Distro is ${DEBTEST}"
elif [[ -f "/etc/redhat-release" ]]; then
  TYPE="rpms"
  PYTHONPACK="/usr/lib/python2.7/site-packages"
  echo "###########################################################################################"
  echo "# Detected linux distribution is RedHat compatible"
  systemctl stop firewalld
  systemctl disable firewalld
  setenforce permissive
else
  echo "Unknown Operating System"
  exit 2
fi

RELEASE=$(curl -sS -k -f "${DOWNLOAD_SERVER}/releases/st2/${VER}/${TYPE}/current/VERSION.txt")
EXIT_CODE=$?

if [ ${EXIT_CODE} -ne 0 ]; then
    echo "Invalid or unsupported version: ${VER}"
    exit 1
fi

# From here on, fail on errors
set -e

STAN="/home/${SYSTEMUSER}/${TYPE}"
mkdir -p ${STAN}
mkdir -p /var/log/st2

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
      echo "${SYSTEMUSER}    ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers.d/st2
    fi
  fi
}

install_pip() {
  echo "###########################################################################################"
  echo "# Installing packages via pip"
  curl -sS -k -o /tmp/requirements.txt https://raw.githubusercontent.com/StackStorm/st2/master/requirements.txt
  pip install -U -q -r /tmp/requirements.txt
}

install_apt() {
  echo "###########################################################################################"
  echo "# Installing packages via apt-get"

  if [ $(grep 'rabbitmq' /etc/apt/sources.list &> /dev/null; echo $?) != 0 ]
  then
    # add rabbitmq APT repo
    echo "########## Adding rabbitmq to sources.list ##########"
    echo 'deb http://www.rabbitmq.com/debian/ testing main' >> /etc/apt/sources.list
    # include public key in trusted key list to avoid warnings
    curl -Ss -k -O http://www.rabbitmq.com/${RABBIT_PUBLIC_KEY}
    sudo apt-key add ${RABBIT_PUBLIC_KEY}
    rm ${RABBIT_PUBLIC_KEY}
  fi
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  # Install packages
  echo "Installing ${APT_PACKAGE_LIST}"
  apt-get install -y ${APT_PACKAGE_LIST}
  setup_rabbitmq
  install_pip
}

install_yum() {
  echo "###########################################################################################"
  echo "# Installing packages via yum"
  rpm --import http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
  curl -sS -k -o /tmp/rabbitmq-server.rpm http://www.rabbitmq.com/releases/rabbitmq-server/v3.3.5/rabbitmq-server-3.3.5-1.noarch.rpm
  yum localinstall -y /tmp/rabbitmq-server.rpm
  echo "Installing ${YUM_PACKAGE_LIST}"
  yum install -y ${YUM_PACKAGE_LIST}
  setup_rabbitmq
  setup_mongodb_systemd
  install_pip
}

setup_rabbitmq() {
  echo "###########################################################################################"
  echo "# Setting up rabbitmq-server"

  # enable rabbitmq-management plugin
  rabbitmq-plugins enable rabbitmq_management

  # Enable rabbit to start on boot
  if [[ "$TYPE" == "rpms" ]]; then
    systemctl enable rabbitmq-server
  fi

  # Restart rabbitmq
  service rabbitmq-server restart

  # use rabbitmqctl to check status
  rabbitmqctl status

  # rabbitmaadmin is useful to inspect exchanges, queues etc.
  curl -sS -o /usr/bin/rabbitmqadmin http://localhost:15672/cli/rabbitmqadmin
  chmod 755 /usr/bin/rabbitmqadmin
}

setup_mysql() {
  if [[ "$TYPE" == "debs" ]]; then
    service mysql restart
  elif [[ "$TYPE" == "rpms" ]]; then
    service mysqld restart
  fi
  if [ $(mysql -uroot -e 'show databases' &> /dev/null; echo $?) == 0 ]
  then
    mysqladmin -u root password StackStorm
  fi
  mysql -uroot -pStackStorm -e "DROP DATABASE IF EXISTS mistral"
  mysql -uroot -pStackStorm -e "CREATE DATABASE mistral"
  mysql -uroot -pStackStorm -e "GRANT ALL PRIVILEGES ON mistral.* TO 'mistral'@'localhost' IDENTIFIED BY 'StackStorm'"
  mysql -uroot -pStackStorm -e "FLUSH PRIVILEGES"
}

setup_mongodb_systemd() {
  # Enable and start MongoDB
  systemctl enable mongod
  systemctl start mongod
}

setup_mistral_config()
{
config=/etc/mistral/mistral.conf
if [ -e "$config" ]; then
    rm $config
fi
touch $config
cat <<mistral_config >$config
[database]
connection=mysql://mistral:StackStorm@localhost/mistral
max_pool_size=50

[pecan]
auth_enable=false
mistral_config
}

setup_mistral_log_config()
{
log_config=/etc/mistral/wf_trace_logging.conf
if [ -e "$log_config" ]; then
    rm $log_config
fi
cp /opt/openstack/mistral/etc/wf_trace_logging.conf.sample $log_config
sed -i "s~tmp~var/log~g" $log_config
}

setup_mistral_upstart()
{
upstart=/etc/init/mistral.conf
if [ -e "$upstart" ]; then
    rm $upstart
fi
touch $upstart
cat <<mistral_upstart >$upstart
description "Mistral Workflow Service"

start on runlevel [2345]
stop on runlevel [016]
respawn

exec /opt/openstack/mistral/.venv/bin/python /opt/openstack/mistral/mistral/cmd/launch.py --config-file /etc/mistral/mistral.conf --log-config-append /etc/mistral/wf_trace_logging.conf
mistral_upstart
}

setup_mistral_systemd()
{
systemd=/etc/systemd/system/mistral.service
if [ -e "$systemd" ]; then
    rm $systemd
fi
touch $systemd
cat <<mistral_systemd >$systemd
[Unit]
Description=Mistral Workflow Service

[Service]
ExecStart=/opt/openstack/mistral/.venv/bin/python /opt/openstack/mistral/mistral/cmd/launch.py --config-file /etc/mistral/mistral.conf --log-file /var/log/mistral.log --log-config-append /etc/mistral/wf_trace_logging.conf
Restart=on-abort

[Install]
WantedBy=multi-user.target
mistral_systemd
systemctl enable mistral
}

setup_mistral() {
  echo "###########################################################################################"
  echo "# Setting up Mistral"

  # Install prerequisites.
  if [[ "$TYPE" == "debs" ]]; then
    apt-get -y install libssl-dev libyaml-dev libffi-dev libxml2-dev libxslt1-dev python-dev libmysqlclient-dev
  elif [[ "$TYPE" == "rpms" ]]; then
    yum -y install openssl-devel libyaml-devel libffi-devel libxml2-devel libxslt-devel python-devel mysql-devel
    # Needed because of mysql-python library
    yum -y install redhat-rpm-config
  fi

  # Clone mistral from github.
  mkdir -p /opt/openstack
  cd /opt/openstack
  if [ -d "/opt/openstack/mistral" ]; then
    rm -r /opt/openstack/mistral
  fi
  git clone -b ${MISTRAL_STABLE_BRANCH} https://github.com/StackStorm/mistral.git

  # Setup virtualenv for running mistral.
  cd /opt/openstack/mistral
  virtualenv --no-site-packages .venv
  . /opt/openstack/mistral/.venv/bin/activate
  pip install -q -r requirements.txt
  pip install -q mysql-python
  python setup.py develop

  # Setup plugins for actions.
  mkdir -p /etc/mistral/actions
  if [ -d "/etc/mistral/actions/st2mistral" ]; then
    rm -r /etc/mistral/actions/st2mistral
  fi
  cd /etc/mistral/actions
  git clone -b ${MISTRAL_STABLE_BRANCH} https://github.com/StackStorm/st2mistral.git
  cd /etc/mistral/actions/st2mistral
  python setup.py develop

  # Create configuration files.
  mkdir -p /etc/mistral
  setup_mistral_config
  setup_mistral_log_config

  # Setup database.
  cd /opt/openstack/mistral
  setup_mysql
  python ./tools/sync_db.py --config-file /etc/mistral/mistral.conf

  # Setup service.
  if [[ "$TYPE" == "debs" ]]; then
    setup_mistral_upstart
  elif [[ "$TYPE" == "rpms" ]]; then
    setup_mistral_systemd
  fi

  # Deactivate venv.
  deactivate

  # Setup mistral client.
  pip install -q -U git+https://github.com/StackStorm/python-mistralclient.git@${MISTRAL_STABLE_BRANCH}
}

function setup_auth() {
    echo "###########################################################################################"
    echo "# Setting up authentication service"

    # Install test htpasswd file
    if [[ ! -f ${AUTH_FILE_PATH} ]]; then
        # File doesn't exist yet
        echo "${HTPASSWD_FILE_CONTENT}" >> ${AUTH_FILE_PATH}
    elif [ -f ${AUTH_FILE_PATH} ] && [ ! `grep -Fxq "${HTPASSWD_FILE_CONTENT}" ${AUTH_FILE_PATH}` ]; then
        # File exists, but the line is not present yet
        echo "${HTPASSWD_FILE_CONTENT}" >> ${AUTH_FILE_PATH}
    fi

    # Configure st2auth to run in standalone mode with the created htpasswd file
    sed -i "s#^mode = proxy\$#mode = standalone#g" ${STANCONF}
    sed -i "s#^backend_kwargs =\$#backend_kwargs = {\"file_path\": \"${AUTH_FILE_PATH}\"}#g" ${STANCONF}
}

download_pkgs() {
  echo "###########################################################################################"
  echo "# Downloading ${TYPE} packages"
  echo "ST2 Packages: ${PACKAGES}"
  pushd ${STAN}
  for pkg in `echo ${PACKAGES} ${CLI_PACKAGE}`
  do
    if [[ "$TYPE" == "debs" ]]; then
      PACKAGE="${pkg}_${VER}-${RELEASE}_amd64.deb"
    elif [[ "$TYPE" == "rpms" ]]; then
      PACKAGE="${pkg}-${VER}-${RELEASE}.noarch.rpm"
    fi

    # Clean up a bit if older versions exist
    old_package=$(ls *${pkg}* 2> /dev/null | wc -l)
    if [ "${old_package}" != "0" ]; then
      rm -f *${pkg}*
    fi

    curl -sS -k -O ${DOWNLOAD_SERVER}/releases/st2/${VER}/${TYPE}/${BUILD}/${PACKAGE}
  done
  popd
}

deploy_rpm() {
  echo "###########################################################################################"
  echo "# Removing any current st2 components"
  for i in `rpm -qa | grep -e "^st2" | grep -v common`; do rpm -e $i; done
  for i in `rpm -qa | grep st2common `; do rpm -e $i; done

  echo "###########################################################################################"
  echo "# Installing st2 ${STAN}"
  pushd ${STAN}
  yum localinstall -y *.rpm
  popd
}

deploy_deb() {
  pushd ${STAN}
  for PACKAGE in $PACKAGES; do
    echo "###########################################################################################"
    echo "# Removing ${PACKAGE}"
    dpkg --purge $PACKAGE
    echo "###########################################################################################"
    echo "# Installing ${PACKAGE} ${VER}"
    dpkg -i ${PACKAGE}*
  done
  popd
}

register_content() {
  echo "###########################################################################################"
  echo "# Registering all content"
  $PYTHON ${PYTHONPACK}/st2common/bin/st2-register-content --register-sensors --register-actions --config-file ${STANCONF}
}

create_user
download_pkgs

if [[ "$TYPE" == "debs" ]]; then
  install_apt

  if [ ${INSTALL_MISTRAL} == "1" ]; then
    setup_mistral
  fi

  deploy_deb
elif [[ "$TYPE" == "rpms" ]]; then
  install_yum

  if [ ${INSTALL_MISTRAL} == "1" ]; then
    setup_mistral
  fi

  deploy_rpm
fi

install_st2client() {
  pushd ${STAN}
  echo "###########################################################################################"
  echo "# Installing st2client requirements via pip"
  curl -sS -k -o /tmp/st2client-requirements.txt https://raw.githubusercontent.com/StackStorm/st2/master/st2client/requirements.txt
  pip install -q -U -r /tmp/st2client-requirements.txt
  if [[ "$TYPE" == "debs" ]]; then
    echo "########## Removing st2client ##########"
    if dpkg -l | grep st2client; then
        apt-get -y purge python-st2client
    fi
    echo "########## Installing st2client ${VER} ##########"
    apt-get -y install gdebi-core
    gdebi --n st2client*
  elif [[ "$TYPE" == "rpms" ]]; then
    yum localinstall -y st2client-${VER}-${RELEASE}.noarch.rpm
  fi
  popd
}

install_webui() {
  echo "###########################################################################################"
  echo "# Installing st2web"
  # Download artifact
  curl -sS -k -f -o /tmp/webui.tar.gz "${DOWNLOAD_SERVER}/releases/st2/${VER}/webui/webui-${VER}.tar.gz"

  # Unpack it into a temporary directory
  temp_dir=$(mktemp -d)
  tar -xzvf /tmp/webui.tar.gz -C ${temp_dir} --strip-components=1

  # Copy the files over to the webui static root
  mkdir -p /opt/stackstorm/static/webui
  cp -R ${temp_dir}/* /opt/stackstorm/static/webui

  # Replace config.js
  echo -e "'use strict';
  angular.module('main')
    .constant('st2Config', {
    hosts: [{
      name: 'StackStorm',
      url: '',
      auth: true 
    }]
  });" > ${WEBUI_CONFIG_PATH}

  # Cleanup
  rm -r ${temp_dir}
  rm -f /tmp/webui.tar.gz
}

setup_auth

if [ ${INSTALL_ST2CLIENT} == "1" ]; then
    install_st2client
fi

if [ ${INSTALL_WEBUI} == "1" ]; then
    install_webui
fi

register_content
echo "###########################################################################################"
echo "# Starting St2 Services"
st2ctl restart
sleep 20
##This is a hack around a weird issue with actions getting stuck in scheduled state
TOKEN=`st2 auth ${TEST_ACCOUNT_USERNAME} -p ${TEST_ACCOUNT_PASSWORD} | grep token | awk '{print $4}'`
ST2_AUTH_TOKEN=${TOKEN} st2 run core.local date &> /dev/null
ACTIONEXIT=$?

echo "=========================================="
echo ""

if [ ! "${ACTIONEXIT}" == 0 ]
then
  echo "ERROR!"
  echo "Something went wrong, st2 failed to start"
  exit 2
else
  echo "          _   ___     ____  _  __ "
  echo "         | | |__ \   / __ \| |/ / "
  echo "      ___| |_   ) | | |  | | ' /  "
  echo "     / __| __| / /  | |  | |  <   "
  echo "     \__ \ |_ / /_  | |__| | . \  "
  echo "     |___/\__|____|  \____/|_|\_\ "
  echo ""
  echo "  st2 is installed and ready to use."
fi

if [ ${INSTALL_WEBUI} == "1" ]; then
  echo "  WebUI at http://`hostname`:9101/webui/"
fi
echo "=========================================="
echo ""

echo "Test StackStorm user account details"
echo ""
echo "Username: ${TEST_ACCOUNT_USERNAME}"
echo "Password: ${TEST_ACCOUNT_PASSWORD}"
echo ""
echo "To login and obtain an authentication token, run the following command:"
echo ""
echo "st2 auth ${TEST_ACCOUNT_USERNAME} -p ${TEST_ACCOUNT_PASSWORD}"
echo ""
echo "For more information see http://docs.stackstorm.com/install/deploy.html#usage"
exit 0
