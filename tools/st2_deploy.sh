#!/bin/bash
set -e

function version_ge() { test "$(echo "$@" | tr " " "\n" | sort -V | tail -n 1)" == "$1"; }

if [ -z $1 ]
then
  VER='0.6.0'
else
  VER=$1
fi

# Determine which mistral version to use
if version_ge $VER "0.8"; then
    MISTRAL_STABLE_BRANCH="st2-0.8.0"
else
    MISTRAL_STABLE_BRANCH="st2-0.5.1"
fi

RABBIT_PUBLIC_KEY="rabbitmq-signing-key-public.asc"
PACKAGES="st2common st2reactor st2actions st2api st2auth st2debug"
CLI_PACKAGE="st2client"
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
    if [ $(grep 'stanley' /etc/sudoers.d/* &> /dev/null; echo $?) != 0 ]
    then
      echo "${SYSTEMUSER}    ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers.d/st2
    fi
  fi
}

install_pip() {

  echo "########## Installing packages via pip ##########"
  curl -sS -k -o /tmp/requirements.txt https://raw.githubusercontent.com/StackStorm/st2/master/requirements.txt
  pip install -U -r /tmp/requirements.txt
}

install_apt(){
  echo "########## Installing packages via apt-get ##########"

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
  aptlist='rabbitmq-server make python-virtualenv python-dev realpath python-pip mongodb mongodb-server gcc git mysql-server'
  echo "Installing ${aptlist}"
  apt-get install -y ${aptlist}
  setup_rabbitmq
  install_pip
}

install_yum() {
  echo "########## Installing packages via yum ##########"
  rpm --import http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
  curl -sS -k -o /tmp/rabbitmq-server.rpm http://www.rabbitmq.com/releases/rabbitmq-server/v3.3.5/rabbitmq-server-3.3.5-1.noarch.rpm
  yum localinstall -y /tmp/rabbitmq-server.rpm
  yumlist='python-pip python-virtualenv python-devel gcc-c++ git-all mongodb mongodb-server mysql-server'
  echo "Installing ${yumlist}"
  yum install -y ${yumlist}
  setup_rabbitmq
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
max_pool_size=100
max_overflow=400
pool_recycle=3600

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
  echo "########## Setting up Mistral ##########"

  # Install prerequisites.
  if [[ "$TYPE" == "debs" ]]; then
    apt-get -y install libssl-dev libyaml-dev libffi-dev libxml2-dev libxslt1-dev python-dev libmysqlclient-dev
  elif [[ "$TYPE" == "rpms" ]]; then
    yum -y install openssl-devel libyaml-devel libffi-devel libxml2-devel libxslt-devel python-devel mysql-devel
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
  pip install -r requirements.txt
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
  pip install -U git+https://github.com/StackStorm/python-mistralclient.git@${MISTRAL_STABLE_BRANCH}
}

download_pkgs() {
  echo "########## Downloading ${TYPE} packages ##########"
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
  $PYTHON ${PYTHONPACK}/st2common/bin/registercontent.py --register-sensors --register-actions --config-file ${STANCONF}
}

create_user
download_pkgs

if [[ "$TYPE" == "debs" ]]; then
  install_apt
  setup_mistral
  deploy_deb
elif [[ "$TYPE" == "rpms" ]]; then
  install_yum
  setup_mistral
  deploy_rpm
fi

install_st2client() {
  pushd ${STAN}
  echo "########## Installing st2client requirements via pip ##########"
  curl -sS -k -o /tmp/st2client-requirements.txt https://raw.githubusercontent.com/StackStorm/st2/master/st2client/requirements.txt
  pip install -U -r /tmp/st2client-requirements.txt
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
  # Download artifact
  curl -sS -k -o /tmp/webui.tar.gz "https://ops.stackstorm.net/releases/st2/${VER}/webui/webui-${VER}-${RELEASE}.tar.gz"

  # Unpack it into a temporary directory
  temp_dir=$(mktemp -d)
  tar -xzvf /tmp/webui.tar.gz -C ${temp_dir} --strip-components=1

  # Copy the files over to the webui static root
  mkdir -p /opt/stackstorm/webui
  cp -R ${temp_dir}/* /opt/stackstorm/webui
}

install_st2client
register_content
echo "########## Starting St2 Services ##########"
st2ctl restart
sleep 20
##This is a hack around a weird issue with actions getting stuck in scheduled state
st2 run core.local date -a &> /dev/null
ACTIONEXIT=$?

echo "=============================="
echo ""

if [ ! "${ACTIONEXIT}" == 0 ]
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
