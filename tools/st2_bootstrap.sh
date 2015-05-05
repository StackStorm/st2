#!/bin/bash

BASE_URL="https://downloads.stackstorm.net/releases/st2"
BOOTSTRAP_FILE="/tmp/st2_boostrap.sh"

STABLE=`curl -Ss -q https://downloads.stackstorm.net/deb/pool/trusty_stable/main/s/st2api/ | grep 'amd64.deb' | sed -e "s~.*>st2api_\(.*\)-.*<.*~\1~g" | sort | uniq | head -n 1`
LATEST=`curl -Ss -q https://downloads.stackstorm.net/deb/pool/trusty_unstable/main/s/st2api/ | grep 'amd64.deb' | sed -e "s~.*>st2api_\(.*\)-.*<.*~\1~g" | sort | uniq head -n 1`

if [ -z $1 ]; then
    ST2VER=0.8.3
else
    if [[ "$1" == "stable" ]]; then
        ST2VER=${STABLE}
    elif [[ "$1" == "latest" ]]; then
        ST2VER=${LATEST}
    else
        ST2VER=$1
    fi
    
fi

DEBTEST=`lsb_release -a 2> /dev/null | grep Distributor | awk '{print $3}'`
RHTEST=`cat /etc/redhat-release 2> /dev/null | sed -e "s~\(.*\)release.*~\1~g"`

if [[ -n "$DEBTEST" ]]; then
  TYPE="debs"
  echo "# Detected Distro is ${DEBTEST}"
elif [[ -n "$RHTEST" ]]; then
  TYPE="rpms"
  echo "# Detected Distro is ${RHTEST}"
else
  echo "Unknown Operating System"
  exit 2
fi

ST2DEPLOY="${BASE_URL}/${ST2VER}/${TYPE}/st2_deploy.sh"
CURLTEST=`curl --output /dev/null --silent --head --fail ${ST2DEPLOY}`

if [ $? -ne 0 ]; then
    echo -e "Unknown version: ${ST2VER}"
    exit 2
else
    echo "Downloading deployment script from: ${ST2DEPLOY}..."
    curl -Ss -k -o ${BOOTSTRAP_FILE} ${ST2DEPLOY}
    chmod +x ${BOOTSTRAP_FILE}

    echo "Running deployment script for St2 ${ST2VER}..."
    bash ${BOOTSTRAP_FILE} ${ST2VER}
fi
