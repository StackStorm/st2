#!/usr/bin/env bash

# Script which installs versions of MongoDB specified using an environment variable

wget http://fastdl.mongodb.org/linux/mongodb-linux-x86_64-${MONGODB}.tgz -O /tmp/mongodb.tgz
tar -xvf /tmp/mongodb.tgz
mkdir /mnt/ramdisk/mongodb
${PWD}/mongodb-linux-x86_64-${MONGODB}/bin/mongod --dbpath /mnt/ramdisk/mongodb --bind_ip 127.0.0.1 &> /dev/null &
