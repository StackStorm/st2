#!/usr/bin/env bash

# Linux system info functions inspired by salt bootstrap script
# https://github.com/saltstack/salt-bootstrap/blob/develop/bootstrap-salt.sh

# Constants
read -r -d '' WARNING_MSG << EOM
######################################################################
######                       DISCLAIMER                        #######
######################################################################

This script installs StackStorm on a single server. Check the docs
for multi-server deployment, hardening security, and other aspects of
running StackStorm in production.

For more information, see http://docs.stackstorm.com/install/index.html
EOM

if [[ $EUID != 0 ]]; then
    echo 'StackStorm installation requires superuser access rights!'
    echo 'Please run with sudo or from root user.'
    exit 1
fi

WARNING_SLEEP_DELAY=5

# Options which can be provied by the user via env variables
INSTALL_ST2CLIENT=${INSTALL_ST2CLIENT:-1}
INSTALL_WEBUI=${INSTALL_WEBUI:-1}
INSTALL_MISTRAL=${INSTALL_MISTRAL:-1}
INSTALL_CLOUDSLANG=${INSTALL_CLOUDSLANG:-0}
INSTALL_WINDOWS_RUNNER_DEPENDENCIES=${INSTALL_WINDOWS_RUNNER_DEPENDENCIES:-1}

# Common variables
DOWNLOAD_SERVER="https://downloads.stackstorm.net"
RABBIT_PUBLIC_KEY="rabbitmq-signing-key-public.asc"
PACKAGES="st2common st2reactor st2actions st2api st2auth st2debug"
IUS_REPO_PKG="https://dl.iuscommunity.org/pub/ius/stable/Redhat/6/x86_64/ius-release-1.0-14.ius.el6.noarch.rpm"
CLI_PACKAGE="st2client"
PIP=`which pip`
VIRTUALENV=`which virtualenv`
PYTHON=`which python2.7`
BUILD="current"
SYSTEMUSER='stanley'
STANCONF="/etc/st2/st2.conf"

CLI_CONFIG_DIRECTORY_PATH=${HOME}/.st2
CLI_CONFIG_RC_FILE_PATH=${CLI_CONFIG_DIRECTORY_PATH}/config

# Information about a test account which used by st2_deploy
TEST_ACCOUNT_USERNAME="testu"
TEST_ACCOUNT_PASSWORD="testp"

# Content for the test htpasswd file used by auth
AUTH_FILE_PATH="/etc/st2/htpasswd"
HTPASSWD_FILE_CONTENT="testu:{SHA}V1t6eZLxnehb7CTBuj61Nq3lIh4="

# Content for the RBAC user role assignment file
ROLE_ASSIGNMENTS_DIRECTORY_PATH="/opt/stackstorm/rbac/assignments/"
ADMIN_USER_ROLE_ASSIGNMENT_FILE_PATH="/opt/stackstorm/rbac/assignments/testu.yaml"
read -r -d '' ADMIN_USER_ROLE_ASSIGNMENT_FILE_CONTENT << EOM
---
    username: "testu"
    roles:
        - "system_admin"
EOM

# WebUI
WEBUI_CONFIG_PATH="/opt/stackstorm/static/webui/config.js"

# CloudSlang variables
CLOUDLSNAG_CLI_VERSION=${CLOUDLSNAG_CLI_VERSION:-cloudslang-0.7.35}
CLOUDLSNAG_CLI_ZIP_NAME=${CLOUDLSNAG_CLI_ZIP_NAME:-cslang-cli-with-content.zip}
CLOUDSLANG_REPO=${CLOUDSLANG_REPO:-CloudSlang/cloud-slang}
CLOUDSLANG_ZIP_URL=https://github.com/${CLOUDSLANG_REPO}/releases/download/${CLOUDLSNAG_CLI_VERSION}/${CLOUDLSNAG_CLI_ZIP_NAME}
CLOUDSLANG_EXEC_PATH=${CLOUDSLANG_EXEC_PATH:-cslang/bin/cslang}

# Common utility functions
function version_ge() { test "$(echo "$@" | tr " " "\n" | sort -V | tail -n 1)" == "$1"; }
function join { local IFS="$1"; shift; echo "$*"; }

# Distribution specific variables
APT_PACKAGE_LIST=("python-pip" "rabbitmq-server" "make" "python-virtualenv" "python-dev" "realpath" "mongodb" "mongodb-server" "gcc" "git")
YUM_PACKAGE_LIST=("gcc-c++" "git-all" "mongodb" "mongodb-server" "mailcap")
YUM_PYTHON_6=("python27" "python27-pip" "python27-virtualenv" "python27-devel")
YUM_PYTHON_7=("python-pip" "python-virtualenv" "python-devel")

# Add windows runner dependencies
# Note: winexe is provided by Stackstorm repos
if [ ${INSTALL_WINDOWS_RUNNER_DEPENDENCIES} == "1" ]; then
  APT_PACKAGE_LIST+=("smbclient" "winexe")
  YUM_PACKAGE_LIST+=("samba-client" "winexe")
fi

if [ ${INSTALL_MISTRAL} == "1" ]; then
  APT_PACKAGE_LIST+=("libssl-dev" "libyaml-dev" "libffi-dev" "libxml2-dev" "libxslt1-dev")
  APT_PACKAGE_LIST+=("postgresql" "postgresql-contrib" "libpq-dev")
  YUM_PACKAGE_LIST+=("openssl-devel" "libyaml-devel" "libffi-devel" "libxml2-devel" "libxslt-devel")
  YUM_PACKAGE_LIST+=("postgresql-server" "postgresql-contrib" "postgresql-devel")
fi

if [ ${INSTALL_CLOUDSLANG} == "1" ]; then
  APT_PACKAGE_LIST+=("unzip" "openjdk-7-jre")
  YUM_PACKAGE_LIST+=("unzip" "java-1.7.0-openjdk")
fi

APT_PACKAGE_LIST=$(join " " ${APT_PACKAGE_LIST[@]})
YUM_PACKAGE_LIST=$(join " " ${YUM_PACKAGE_LIST[@]})

STABLE=`curl -Ss -q https://downloads.stackstorm.net/deb/pool/trusty_stable/main/s/st2api/ | grep 'amd64.deb' | sed -e "s~.*>st2api_\(.*\)-.*<.*~\1~g" | sort --version-sort -r | uniq | head -n 1`
LATEST=`curl -Ss -q https://downloads.stackstorm.net/deb/pool/trusty_unstable/main/s/st2api/ | grep 'amd64.deb' | sed -e "s~.*>st2api_\(.*\)-.*<.*~\1~g" | sort --version-sort -r | uniq | head -n 1`

# Actual code starts here

echo "${WARNING_MSG}"
echo ""
echo "To abort press CTRL-C otherwise installation will continue in ${WARNING_SLEEP_DELAY} seconds"
sleep ${WARNING_SLEEP_DELAY}

echo "Checking for space availability for MongoDB. MongoDB requires at least 3Gb free in /var/lib/..."
echo ""
VAR_SPACE=`df -Pk /var/lib | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{print $4}'`
if [ ${VAR_SPACE} -lt 3500000 ]
then
  echo "There is not enough space for MongoDB. It will fail to start. Please, add some space to /var or clean it up."
  exit 1
fi

if [ -z $1 ]
then
  VER=${STABLE}
elif [[ "$1" == "latest" ]]; then
   VER=${LATEST}
else
  VER=$1
fi

echo "Installing version ${VER}"

# Determine which mistral version to use
if version_ge $VER "0.13"; then
    MISTRAL_STABLE_BRANCH="st2-0.13.0"
elif version_ge $VER "0.9"; then
    MISTRAL_STABLE_BRANCH="st2-0.9.0"
elif version_ge $VER "0.8.1"; then
    MISTRAL_STABLE_BRANCH="st2-0.8.1"
elif version_ge $VER "0.8"; then
    MISTRAL_STABLE_BRANCH="st2-0.8.0"
else
    MISTRAL_STABLE_BRANCH="st2-0.5.1"
fi

#######  ADDING IN DISTRO DISCOVERY FROM SALT BOOTSTRAP

#---  FUNCTION  -------------------------------------------------------------------------------------------------------
#          NAME:  __camelcase_split
#   DESCRIPTION:  Convert CamelCased strings to Camel_Cased
#----------------------------------------------------------------------------------------------------------------------
__camelcase_split() {
    echo "${@}" | sed -r 's/([^A-Z-])([A-Z])/\1 \2/g'
}

#---  FUNCTION  -------------------------------------------------------------------------------------------------------
#          NAME:  __parse_version_string
#   DESCRIPTION:  Parse version strings ignoring the revision.
#                 MAJOR.MINOR.REVISION becomes MAJOR.MINOR
#----------------------------------------------------------------------------------------------------------------------
__parse_version_string() {
    VERSION_STRING="$1"
    PARSED_VERSION=$(
        echo "$VERSION_STRING" |
        sed -e 's/^/#/' \
            -e 's/^#[^0-9]*\([0-9][0-9]*\.[0-9][0-9]*\)\(\.[0-9][0-9]*\).*$/\1/' \
            -e 's/^#[^0-9]*\([0-9][0-9]*\.[0-9][0-9]*\).*$/\1/' \
            -e 's/^#[^0-9]*\([0-9][0-9]*\).*$/\1/' \
            -e 's/^#.*$//'
    )
    echo "$PARSED_VERSION"
}

#---  FUNCTION  -------------------------------------------------------------------------------------------------------
#          NAME:  __sort_release_files
#   DESCRIPTION:  Custom sort function. Alphabetical or numerical sort is not
#                 enough.
#----------------------------------------------------------------------------------------------------------------------
__sort_release_files() {
    KNOWN_RELEASE_FILES=$(echo "(arch|centos|debian|ubuntu|fedora|redhat|suse|\
        mandrake|mandriva|gentoo|slackware|turbolinux|unitedlinux|lsb|system|\
        oracle|os)(-|_)(release|version)" | sed -r 's:[[:space:]]::g')
    primary_release_files=""
    secondary_release_files=""
    # Sort know VS un-known files first
    for release_file in $(echo "${@}" | sed -r 's:[[:space:]]:\n:g' | sort --unique --ignore-case); do
        match=$(echo "$release_file" | egrep -i "${KNOWN_RELEASE_FILES}")
        if [ "${match}" != "" ]; then
            primary_release_files="${primary_release_files} ${release_file}"
        else
            secondary_release_files="${secondary_release_files} ${release_file}"
        fi
    done

    # Now let's sort by know files importance, max important goes last in the max_prio list
    max_prio="redhat-release centos-release oracle-release"
    for entry in $max_prio; do
        if [ "$(echo "${primary_release_files}" | grep "$entry")" != "" ]; then
            primary_release_files=$(echo "${primary_release_files}" | sed -e "s:\(.*\)\($entry\)\(.*\):\2 \1 \3:g")
        fi
    done
    # Now, least important goes last in the min_prio list
    min_prio="lsb-release"
    for entry in $min_prio; do
        if [ "$(echo "${primary_release_files}" | grep "$entry")" != "" ]; then
            primary_release_files=$(echo "${primary_release_files}" | sed -e "s:\(.*\)\($entry\)\(.*\):\1 \3 \2:g")
        fi
    done

    # Echo the results collapsing multiple white-space into a single white-space
    echo "${primary_release_files} ${secondary_release_files}" | sed -r 's:[[:space:]]+:\n:g'
}

#---  FUNCTION  -------------------------------------------------------------------------------------------------------
#          NAME:  __gather_linux_system_info
#   DESCRIPTION:  Discover Linux system information
#----------------------------------------------------------------------------------------------------------------------
__gather_linux_system_info() {
    DISTRO_NAME=""
    DISTRO_VERSION=""
    # Let's test if the lsb_release binary is available
    rv=$(lsb_release >/dev/null 2>&1)
    if [ $? -eq 0 ]; then
        DISTRO_NAME=$(lsb_release -si)
        if [ "${DISTRO_NAME}" = "Scientific" ]; then
            DISTRO_NAME="Scientific Linux"
        elif [ "$(echo "$DISTRO_NAME" | grep RedHat)" != "" ]; then
            # Let's convert CamelCase to Camel Case
            DISTRO_NAME=$(__camelcase_split "$DISTRO_NAME")
        elif [ "${DISTRO_NAME}" = "openSUSE project" ]; then
            # lsb_release -si returns "openSUSE project" on openSUSE 12.3
            DISTRO_NAME="opensuse"
        elif [ "${DISTRO_NAME}" = "SUSE LINUX" ]; then
            if [ "$(lsb_release -sd | grep -i opensuse)" != "" ]; then
                # openSUSE 12.2 reports SUSE LINUX on lsb_release -si
                DISTRO_NAME="opensuse"
            else
                # lsb_release -si returns "SUSE LINUX" on SLES 11 SP3
                DISTRO_NAME="suse"
            fi
        elif [ "${DISTRO_NAME}" = "EnterpriseEnterpriseServer" ]; then
            # This the Oracle Linux Enterprise ID before ORACLE LINUX 5 UPDATE 3
            DISTRO_NAME="Oracle Linux"
        elif [ "${DISTRO_NAME}" = "OracleServer" ]; then
            # This the Oracle Linux Server 6.5
            DISTRO_NAME="Oracle Linux"
        elif [ "${DISTRO_NAME}" = "AmazonAMI" ]; then
            DISTRO_NAME="Amazon Linux AMI"
        elif [ "${DISTRO_NAME}" = "Arch" ]; then
            DISTRO_NAME="Arch Linux"
            return
        fi
        rv=$(lsb_release -sr)
        [ "${rv}" != "" ] && DISTRO_VERSION=$(__parse_version_string "$rv")
    elif [ -f /etc/lsb-release ]; then
        # We don't have the lsb_release binary, though, we do have the file it parses
        DISTRO_NAME=$(grep DISTRIB_ID /etc/lsb-release | sed -e 's/.*=//')
        rv=$(grep DISTRIB_RELEASE /etc/lsb-release | sed -e 's/.*=//')
        [ "${rv}" != "" ] && DISTRO_VERSION=$(__parse_version_string "$rv")
    fi
    if [ "$DISTRO_NAME" != "" ] && [ "$DISTRO_VERSION" != "" ]; then
        # We already have the distribution name and version
        return
    fi
    # shellcheck disable=SC2035,SC2086
    for rsource in $(__sort_release_files "$(
            cd /etc && /bin/ls *[_-]release *[_-]version 2>/dev/null | env -i sort | \
            sed -e '/^redhat-release$/d' -e '/^lsb-release$/d'; \
            echo redhat-release lsb-release
            )"); do
        [ -L "/etc/${rsource}" ] && continue        # Don't follow symlinks
        [ ! -f "/etc/${rsource}" ] && continue      # Does not exist
        n=$(echo "${rsource}" | sed -e 's/[_-]release$//' -e 's/[_-]version$//')
        shortname=$(echo "${n}" | tr '[:upper:]' '[:lower:]')
        if [ "$shortname" = "debian" ]; then
            rv=$(__derive_debian_numeric_version "$(cat /etc/${rsource})")
        else
            rv=$( (grep VERSION "/etc/${rsource}"; cat "/etc/${rsource}") | grep '[0-9]' | sed -e 'q' )
        fi
        [ "${rv}" = "" ] && [ "$shortname" != "arch" ] && continue  # There's no version information. Continue to next rsource
        v=$(__parse_version_string "$rv")
        case $shortname in
            redhat             )
                if [ "$(egrep 'CentOS' /etc/${rsource})" != "" ]; then
                    n="CentOS"
                elif [ "$(egrep 'Scientific' /etc/${rsource})" != "" ]; then
                    n="Scientific Linux"
                elif [ "$(egrep 'Red Hat Enterprise Linux' /etc/${rsource})" != "" ]; then
                    n="Red Hat Enterprise Server"
                fi
                ;;
            arch               ) n="Arch Linux"     ;;
            centos             ) n="CentOS"         ;;
            debian             ) n="Debian"         ;;
            ubuntu             ) n="Ubuntu"         ;;
            fedora             ) n="Fedora"         ;;
            suse               ) n="SUSE"           ;;
            mandrake*|mandriva ) n="Mandriva"       ;;
            gentoo             ) n="Gentoo"         ;;
            slackware          ) n="Slackware"      ;;
            turbolinux         ) n="TurboLinux"     ;;
            unitedlinux        ) n="UnitedLinux"    ;;
            oracle             ) n="Oracle Linux"   ;;
            system             )
                while read -r line; do
                    [ "${n}x" != "systemx" ] && break
                    case "$line" in
                        *Amazon*Linux*AMI*)
                            n="Amazon Linux AMI"
                            break
                    esac
                done < "/etc/${rsource}"
                ;;
            os                 )
                nn="$(__unquote_string "$(grep '^ID=' /etc/os-release | sed -e 's/^ID=\(.*\)$/\1/g')")"
                rv="$(__unquote_string "$(grep '^VERSION_ID=' /etc/os-release | sed -e 's/^VERSION_ID=\(.*\)$/\1/g')")"
                [ "${rv}" != "" ] && v=$(__parse_version_string "$rv") || v=""
                case $(echo "${nn}" | tr '[:upper:]' '[:lower:]') in
                    amzn        )
                        # Amazon AMI's after 2014.9 match here
                        n="Amazon Linux AMI"
                        ;;
                    arch        )
                        n="Arch Linux"
                        v=""  # Arch Linux does not provide a version.
                        ;;
                    debian      )
                        n="Debian"
                        v=$(__derive_debian_numeric_version "$v")
                        ;;
                    *           )
                        n=${nn}
                        ;;
                esac
                ;;
            *                  ) n="${n}"           ;
        esac
        DISTRO_NAME=$n
        DISTRO_VERSION=$v
        break
    done
}

__gather_linux_system_info

######### END SALT BOOTSTRAP DISTRO INFO

echo "###########################################################################################"
echo "# Detected Distro is ${DISTRO_NAME} ${DISTRO_VERSION}"

if [[ "${DISTRO_NAME}" == "Ubuntu" ]]; then
  TYPE="debs"
  PYTHONPACK="/usr/lib/python2.7/dist-packages"
elif [[ "${DISTRO_NAME}" == "Red Hat Enterprise Server" ]] || [[ "${DISTRO_NAME}" == "Fedora" ]] || [[ "${DISTRO_NAME}" == "CentOS" ]] || [[ "${DISTRO_NAME}" == "Scientific Linux" ]]; then
  TYPE="rpms"
  PYTHONPACK="/usr/lib/python2.7/site-packages"

  if [[ ${DISTRO_VERSION} =~ 7\.[0-9] ]] || [[ "${DISTRO_NAME}" == "Fedora" ]]
  then
    if [[ "${DISTRO_NAME}" == "Fedora" ]]
    then
      systemctl stop firewalld
      systemctl disable firewalld
    fi
    YUM_PYTHON=$(join " " ${YUM_PYTHON_7[@]})
  elif [[ $DISTRO_VERSION =~ 6\.[0-9] ]]
  then
    service firewalld stop
    chkconfig firewalld off
    PYTHON="python2.7"
    PIP="pip2.7"
    VIRTUALENV="virtualenv-2.7"
    YUM_PYTHON=$(join " " ${YUM_PYTHON_6[@]})
  else
    echo "Unknown RHEL-family... Aborting install."
    exit 2
  fi

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
  fi
  if [ $(grep ${SYSTEMUSER} /etc/sudoers.d/* &> /dev/null; echo $?) != 0 ]
  then
    echo "${SYSTEMUSER}    ALL=(ALL)       NOPASSWD: SETENV: ALL" >> /etc/sudoers.d/st2
    chmod 0440 /etc/sudoers.d/st2
  fi

  # make sure requiretty is disabled.
  sed -i "s/^Defaults\s\+requiretty/# Defaults requiretty/g" /etc/sudoers
}

install_pip() {
  echo "###########################################################################################"
  echo "# Installing packages via pip"
  ${PIP} install -U pip
  hash -d ${PIP}
  curl -sS -k -o /tmp/requirements.txt https://raw.githubusercontent.com/StackStorm/st2/master/requirements.txt
  ${PIP} install -U -r /tmp/requirements.txt
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

  # Add StackStorm APT repo
  echo "deb http://downloads.stackstorm.net/deb/ trusty_unstable main" > /etc/apt/sources.list.d/stackstorm.list
  curl -Ss -k ${DOWNLOAD_SERVER}/deb/pubkey.gpg -o /tmp/stackstorm.repo.pubkey.gpg
  sudo apt-key add /tmp/stackstorm.repo.pubkey.gpg

  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  # Install packages
  echo "Installing ${APT_PACKAGE_LIST}"
  apt-get install -y ${APT_PACKAGE_LIST}
  # Now that pip is installed set PIP=`which pip` again.
  PIP=`which pip`
  setup_rabbitmq
  install_pip
}

install_yum() {
  echo "###########################################################################################"
  echo "# Installing packages via yum"
  if [[ "$DISTRO_NAME" == "Red Hat Enterprise Server" ]] || [[ "${DISTRO_NAME}" == "CentOS" ]] || [[ "${DISTRO_NAME}" == "Scientific Linux" ]]
  then
    if [[ $DISTRO_VERSION =~ 6\.[0-9] ]]
    then
      if ! rpm -qa | grep -q ius-release
      then
        yum install -t -y ${IUS_REPO_PKG}
      fi
    fi
    yum install -y epel-release
  fi
  yum update -y
  rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
  curl -sS -k -o /tmp/rabbitmq-server.rpm https://www.rabbitmq.com/releases/rabbitmq-server/v3.3.5/rabbitmq-server-3.3.5-1.noarch.rpm
  yum localinstall -y /tmp/rabbitmq-server.rpm

  # Add StackStorm YUM repo
  sudo bash -c "cat > /etc/yum.repos.d/stackstorm.repo" <<EOL
[st2-f20-deps]
Name=StackStorm Dependencies Fedora repository
baseurl=${DOWNLOAD_SERVER}/rpm/fedora/20/deps/
enabled=1
gpgcheck=0
EOL
  echo "Installing required Python packages: ${YUM_PYTHON}"
  yum install -y ${YUM_PYTHON}
  echo "Installing other required packages: ${YUM_PACKAGE_LIST}"
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
    chkconfig rabbitmq-server on
  fi

  # Restart rabbitmq
  service rabbitmq-server restart

  # use rabbitmqctl to check status
  rabbitmqctl status

  # rabbitmqadmin is useful to inspect exchanges, queues etc.
  curl -sS -o /usr/bin/rabbitmqadmin http://127.0.0.1:15672/cli/rabbitmqadmin
  chmod 755 /usr/bin/rabbitmqadmin
}

setup_mongodb_systemd() {
  # Enable and start MongoDB
  if ([[ "${DISTRO_NAME}" == "Red Hat Enterprise Server" ]] || [[ "${DISTRO_NAME}" == "CentOS" ]] || [[ "${DISTRO_NAME}" == "Scientific Linux" ]]) && [[ $DISTRO_VERSION =~ 7\.[0-9] ]]
  then
    systemctl enable mongod
    systemctl start mongod
  else
    chkconfig mongod on
    service mongod start
  fi
}

setup_mistral_st2_config()
{
  echo "" >> ${STANCONF}
  echo "[mistral]" >> ${STANCONF}
  echo "v2_base_url = http://127.0.0.1:8989/v2" >> ${STANCONF}
}

setup_postgresql() {
  # Setup the postgresql service on Fedora. Ubuntu is already setup by default.
  if [[ "$TYPE" == "rpms" ]]; then
    echo "Configuring PostgreSQL..."

    if (([[ "${DISTRO_NAME}" == "Red Hat Enterprise Server" ]] || [[ "${DISTRO_NAME}" == "CentOS" ]] || [[ "${DISTRO_NAME}" == "Scientific Linux" ]]) && [[ $DISTRO_VERSION =~ 7\.[0-9] ]]) || [[ "${DISTRO_NAME}" == "Fedora" ]]
    then
      systemctl enable postgresql
      if postgresql-setup initdb
      then
        pg_hba_config=/var/lib/pgsql/data/pg_hba.conf
        sed -i 's/^local\s\+all\s\+all\s\+peer/local all all trust/g' ${pg_hba_config}
        sed -i 's/^local\s\+all\s\+all\s\+ident/local all all trust/g' ${pg_hba_config}
        sed -i 's/^host\s\+all\s\+all\s\+127.0.0.1\/32\s\+ident/host all all 127.0.0.1\/32 md5/g' ${pg_hba_config}
        sed -i 's/^host\s\+all\s\+all\s\+::1\/128\s\+ident/host all all ::1\/128 md5/g' ${pg_hba_config}
      fi
      systemctl start postgresql
    else
      chkconfig postgresql on
      if service postgresql initdb
      then
        pg_hba_config=/var/lib/pgsql/data/pg_hba.conf
        sed -i 's/^local\s\+all\s\+all\s\+peer/local all all trust/g' ${pg_hba_config}
        sed -i 's/^local\s\+all\s\+all\s\+ident/local all all trust/g' ${pg_hba_config}
        sed -i 's/^host\s\+all\s\+all\s\+127.0.0.1\/32\s\+ident/host all all 127.0.0.1\/32 md5/g' ${pg_hba_config}
        sed -i 's/^host\s\+all\s\+all\s\+::1\/128\s\+ident/host all all ::1\/128 md5/g' ${pg_hba_config}
      fi
      service postgresql start
    fi
  fi

  echo "Changing max connections for PostgreSQL..."
  config=`sudo -u postgres psql -c "SHOW config_file;" | grep postgresql.conf`
  sed -i 's/max_connections = 100/max_connections = 500/' ${config}
  service postgresql restart
}

setup_mistral_config()
{
config=/etc/mistral/mistral.conf
echo "Writing Mistral configuration file to $config..."
if [ -e "$config" ]; then
  rm $config
fi
touch $config
cat <<mistral_config >$config
[database]
connection=postgresql://mistral:StackStorm@localhost/mistral
max_pool_size=50

[pecan]
auth_enable=false
mistral_config
}

setup_mistral_log_config()
{
log_config=/etc/mistral/wf_trace_logging.conf
echo "Writing Mistral log configuration file to $log_config..."
if [ -e "$log_config" ]; then
    rm $log_config
fi
cp /opt/openstack/mistral/etc/wf_trace_logging.conf.sample $log_config
sed -i "s~tmp~var/log~g" $log_config
}

setup_mistral_db()
{
  set +e
  service mistral stop
  set -e
  echo "Setting up Mistral DB in PostgreSQL..."
  sudo -u postgres psql -c "DROP DATABASE IF EXISTS mistral;"
  sudo -u postgres psql -c "DROP USER IF EXISTS mistral;"
  sudo -u postgres psql -c "CREATE USER mistral WITH ENCRYPTED PASSWORD 'StackStorm';"
  sudo -u postgres psql -c "CREATE DATABASE mistral OWNER mistral;"

  echo "Creating and populating DB tables for Mistral..."
  config=/etc/mistral/mistral.conf
  cd /opt/openstack/mistral
  /opt/openstack/mistral/.venv/bin/python ./tools/sync_db.py --config-file ${config}
}

setup_mistral_upstart()
{
echo "Setting up upstart for Mistral..."
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
echo "Setting up systemd for Mistral..."
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


setup_mistral_initd()
{
echo "Setting up initd script for Mistral..."
initd=/etc/init.d/mistral
if [ -e "$initd" ]; then
    rm $initd
fi
touch $initd
chmod +x $initd

cat <<mistral_initd >$initd
#!/bin/sh
#
# mistral        This shell script takes care of starting and stopping
#               the mistral subsystem (mistral).
#
# chkconfig: - 64 36
# description:  Mistral.
# processname: mistral
# config: /etc/mistral/mistral.conf
# pidfile: /var/run/mistral/mistral.pid
### BEGIN INIT INFO
# Provides: mistral
# Required-Start: \$local_fs \$remote_fs \$network \$named \$syslog \$time
# Required-Stop: \$local_fs \$remote_fs \$network \$named \$syslog \$time
# Short-Description: start mistral
# Description: Mistral
### END INIT INFO

# Source function library.
. /etc/rc.d/init.d/functions

# Source networking configuration.
. /etc/sysconfig/network

exec="/opt/openstack/mistral/.venv/bin/python2.7"
prog="mistral"


# Set timeouts here so they can be overridden from /etc/sysconfig/mistral
STARTTIMEOUT=120
STOPTIMEOUT=60
MYOPTIONS=

[ -e /etc/sysconfig/\$prog ] && . /etc/sysconfig/\$prog

lockfile=/var/lock/subsys/\$prog


start(){
    [ -x \$exec ] || exit 5
    RESPONSE=\`/bin/ps aux | /bin/grep mistral | /bin/grep launch | wc -l 2> /dev/null\`
    if [ \$RESPONSE -gt 0 ]; then
        # already running, do nothing
        echo "Mistral is already running..."
        ret=0
    else
        action \$"Starting \$prog: " /bin/true
        \$exec /opt/openstack/mistral/mistral/cmd/launch.py --config-file /etc/mistral/mistral.conf --log-file /var/log/mistral.log --log-config-append /etc/mistral/wf_trace_logging.conf > /dev/null 2>&1 &
    fi
    return \$ret
}

stop(){
      PID=\`ps ax | grep -v grep | grep mistral | grep openstack | awk '{print \$1}'\`
      if [[ ! -z \$PID ]]
      then
        for p in \$PID
        do
           echo "Killing mistral PID: \${p}"
           #ps \${p}
           kill \${p}
        done
        action \$"Stopping \$prog: " /bin/true
      else
        echo "mistral is not running"
        action \$"Stopping \$prog: " /bin/false
      fi
}



restart(){
        stop
        start
}

# See how we were called.
case "\$1" in
  start)
    start
    ;;
  startsos)
    start sos
    ;;
  stop)
    stop
    ;;
  status)
    status \$prog
    ;;
  restart)
    restart
    ;;
  condrestart|try-restart)
    condrestart
    ;;
  reload)
    exit 3
    ;;
  force-reload)
    restart
    ;;
  *)
    echo \$"Usage: \$0 {start|stop|status|restart|condrestart|try-restart|reload|force-reload|startsos}"
    exit 2
esac

exit \$?
mistral_initd
chkconfig mistral on


}



setup_mistral() {
  echo "###########################################################################################"
  echo "# Setting up Mistral"

  # Clone mistral from github.
  mkdir -p /opt/openstack
  cd /opt/openstack
  if [ -d "/opt/openstack/mistral" ]; then
    rm -r /opt/openstack/mistral
  fi
  echo "Cloning Mistral branch: ${MISTRAL_STABLE_BRANCH}..."
  git clone -b ${MISTRAL_STABLE_BRANCH} https://github.com/StackStorm/mistral.git

  # Setup virtualenv for running mistral.
  cd /opt/openstack/mistral
  ${VIRTUALENV} --no-site-packages .venv
  . /opt/openstack/mistral/.venv/bin/activate
  pip install -U setuptools
  pip install -q -r requirements.txt
  pip install -q psycopg2
  python setup.py install

  # Setup plugins for actions.
  mkdir -p /etc/mistral/actions
  if [ -d "/etc/mistral/actions/st2mistral" ]; then
    rm -r /etc/mistral/actions/st2mistral
  fi
  echo "Cloning St2mistral branch: ${MISTRAL_STABLE_BRANCH}..."
  cd /etc/mistral/actions
  git clone -b ${MISTRAL_STABLE_BRANCH} https://github.com/StackStorm/st2mistral.git
  cd /etc/mistral/actions/st2mistral
  python setup.py install

  # Create configuration files.
  mkdir -p /etc/mistral
  setup_mistral_config
  setup_mistral_log_config
  setup_mistral_st2_config

  # Setup service.
  if [[ "$TYPE" == "debs" ]]; then
    setup_mistral_upstart
  elif [[ "$TYPE" == "rpms" ]]; then
    if [[ $DISTRO_VERSION =~ 7\.[0-9] ]] || [[ "$DISTRO_NAME" == "Fedora" ]]
    then
      setup_mistral_systemd
    else
      setup_mistral_initd
    fi
  fi

  # Setup database.
  setup_postgresql
  setup_mistral_db

  # Deactivate venv.
  deactivate

  # Setup mistral client.
  ${PIP} install -q -U git+https://github.com/StackStorm/python-mistralclient.git@${MISTRAL_STABLE_BRANCH}
}

setup_cloudslang() {
  echo "###########################################################################################"
  echo "# Setting up CloudSlang"

  cd /opt
  if [ -d "/opt/cslang" ]; then
    rm -rf /opt/cslang
  fi

  echo "Downloading CloudSlang CLI"
  curl -Ss -Lk -o cslang-cli.zip ${CLOUDSLANG_ZIP_URL}

  echo "Unzipping CloudSlang CLI"
  unzip cslang-cli.zip

  echo "Chmoding CloudSlang executables"
  chmod +x ${CLOUDSLANG_EXEC_PATH}

  echo "Deleting cslang-cli zip file"
  rm cslang-cli.zip
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

function setup_admin_user() {
    echo "###########################################################################################"
    echo "# Setting up admin user"

    mkdir -p ${ROLE_ASSIGNMENTS_DIRECTORY_PATH}

    # Install role definition file for an admin user
    if [[ ! -f ${ADMIN_USER_ROLE_ASSIGNMENT_FILE_PATH} ]]; then
        echo "${ADMIN_USER_ROLE_ASSIGNMENT_FILE_CONTENT}" > ${ADMIN_USER_ROLE_ASSIGNMENT_FILE_PATH}
    fi
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

migrate_rules() {
  echo "###########################################################################################"
  echo "# Migrating rules (pack inclusion)."
  $PYTHON ${PYTHONPACK}/st2common/bin/migrate_rules_to_include_pack.py
}

migrate_triggers() {
  echo "###########################################################################################"
  echo "# Migrating triggers (ref_count inclusion)."
  $PYTHON ${PYTHONPACK}/st2common/bin/migrate_triggers_to_include_ref_count.py
}

register_content() {
  echo "###########################################################################################"
  echo "# Registering all content"
  ${PYTHON} ${PYTHONPACK}/st2common/bin/st2-register-content --register-sensors --register-actions --config-file ${STANCONF}
}

function apply_rbac_definitions() {
  echo "###########################################################################################"
  echo "# Applying RBAC definitions"
  ${PYTHON} ${PYTHONPACK}/st2common/bin/st2-apply-rbac-definitions --config-file ${STANCONF}
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

if [ ${INSTALL_MISTRAL} == "1" ]; then
  setup_mistral
fi

if [ ${INSTALL_CLOUDSLANG} == "1" ]; then
  setup_cloudslang
fi

install_st2client() {
  pushd ${STAN}
  echo "###########################################################################################"
  echo "# Installing st2client requirements via pip"
  curl -sS -k -o /tmp/st2client-requirements.txt https://raw.githubusercontent.com/StackStorm/st2/master/st2client/requirements.txt
  ${PIP} install -q -U -r /tmp/st2client-requirements.txt
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

  # Write ST2_BASE_URL to env
  if [[ "$TYPE" == "rpms" ]]; then
    BASHRC=/etc/bashrc
    echo "" >> ${BASHRC}
    echo "export ST2_BASE_URL='http://127.0.0.1'" >> ${BASHRC}
  fi

  # Delete existing config directory (if exists)
  if [ -e "${CLI_CONFIG_DIRECTORY_PATH}" ]; then
    rm -r ${CLI_CONFIG_DIRECTORY_PATH}
  fi

  # Write the CLI config file with the default credentials
  mkdir -p ${CLI_CONFIG_DIRECTORY_PATH}

  bash -c "cat > ${CLI_CONFIG_RC_FILE_PATH}" <<EOL
[general]
base_url = http://127.0.0.1

[credentials]
username = ${TEST_ACCOUNT_USERNAME}
password = ${TEST_ACCOUNT_PASSWORD}
EOL
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
      url: '//:9101',
      auth: '//:9100'
    }]
  });" > ${WEBUI_CONFIG_PATH}

  sed -i "s%^# allow_origin =.*\$%allow_origin = *%g" ${STANCONF}

  # Cleanup
  rm -r ${temp_dir}
  rm -f /tmp/webui.tar.gz
}

setup_auth
setup_admin_user

if [ ${INSTALL_ST2CLIENT} == "1" ]; then
    install_st2client
fi

if [ ${INSTALL_WEBUI} == "1" ]; then
    install_webui
fi

if version_ge $VER "0.9"; then
  migrate_rules
fi

if version_ge $VER "1.0"; then
  migrate_triggers
fi

register_content
apply_rbac_definitions

echo "###########################################################################################"
echo "# Starting St2 Services"

st2ctl restart
sleep 20
##This is a hack around a weird issue with actions getting stuck in scheduled state
TOKEN=`st2 auth ${TEST_ACCOUNT_USERNAME} -p ${TEST_ACCOUNT_PASSWORD} | grep token | awk '{print $4}'`
ST2_AUTH_TOKEN=${TOKEN} st2 run core.local date &> /dev/null
ACTIONEXIT=$?
## Clean up token
rm -Rf /home/${SYSTEMUSER}/.st2
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

echo "=========================================="
echo ""

echo "Test StackStorm user account details"
echo ""
echo "Username: ${TEST_ACCOUNT_USERNAME}"
echo "Password: ${TEST_ACCOUNT_PASSWORD}"
echo ""
echo "Test account credentials were also written to the default CLI config at ${CLI_CONFIG_PATH}."
echo ""
echo "To login and obtain an authentication token, run the following command:"
echo ""
echo "st2 auth ${TEST_ACCOUNT_USERNAME} -p ${TEST_ACCOUNT_PASSWORD}"
echo ""
echo "For more information see http://docs.stackstorm.com/authentication.html#usage"
exit 0
