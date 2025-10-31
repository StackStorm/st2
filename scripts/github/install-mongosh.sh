#!/usr/bin/env bash

# Some GHA require mongosh, which isn't nativefly available on ubuntu 22.04

set -x

sudo apt-get update
sudo apt-get install -y curl
OS_CODENAME=$(
# shellcheck disable=SC1091
source /etc/os-release
echo "${VERSION_CODENAME}"
)
export OS_CODENAME
echo "Detected os codename: ${OS_CODENAME}"

# Add MongoDB (7.0) repository signing key and apt repository
curl -1sLf https://pgp.mongodb.com/server-7.0.asc | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/mongodb-org-7.0.gpg
echo "deb http://repo.mongodb.org/apt/ubuntu ${OS_CODENAME}/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

sudo apt-get update
sudo apt-get install -y mongodb-mongosh
