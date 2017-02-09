#!/usr/bin/env bash

# Script which installs versions of MongoDB specified using an environment variable
if [ ! "${MONGODB_VERSION}" ]; then
    echo "MONGODB_VERSION environment variable not set."
    exit 2
fi

DATA_DIR=/tmp/mongodbdata
MONGODB_DIR=/tmp/mongodb

mkdir -p ${DATA_DIR}
mkdir -p ${MONGODB_DIR}

wget -q http://fastdl.mongodb.org/linux/mongodb-linux-x86_64-${MONGODB_VERSION}.tgz -O /tmp/mongodb.tgz
tar -xvf /tmp/mongodb.tgz -C ${MONGODB_DIR} --strip=1
echo "Starting MongoDB v${MONGODB_VERSION}"
${MONGODB_DIR}/bin/mongod --nojournal --journalCommitInterval 500 \
    --syncdelay 0 --dbpath ${DATA_DIR} --bind_ip 127.0.0.1 &> /tmp/mongodb.log &
EXIT_CODE=$?
sleep 5

if [ ${EXIT_CODE} -ne 0 ]; then
    echo "Failed to start MongoDB"
    tail -30 /tmp/mongodb.log
    exit 1
fi

tail -30 /tmp/mongodb.log
