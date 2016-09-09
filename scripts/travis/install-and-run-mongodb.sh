#!/usr/bin/env bash

# Script which installs versions of MongoDB specified using an environment variable

# Note: MongoDB 2.4 and 2.6 don't work with ramdisk since they don't work with
# small files and require at least 3 GB of space
if [ ${MONGODB} = '2.4.9' ] || [ ${MONGODB} = '2.6.12' ]; then
    DATA_DIR=/tmp/mongodbdata
else
    DATA_DIR=/mnt/ramdisk/mongodb
fi

wget http://fastdl.mongodb.org/linux/mongodb-linux-x86_64-${MONGODB}.tgz -O /tmp/mongodb.tgz
tar -xvf /tmp/mongodb.tgz
mkdir -p ${DATA_DIR}
echo "Starting MongoDB v${MONGODB}"
${PWD}/mongodb-linux-x86_64-${MONGODB}/bin/mongod --nojournal --journalCommitInterval 500 \
    --syncdelay 0 --dbpath ${DATA_DIR} --bind_ip 127.0.0.1 &> /tmp/mongodb.log &
EXIT_CODE=$?
sleep 5

if [ ${EXIT_CODE} -ne 0 ]; then
    echo "Failed to start MongoDB"
    tail -30 /tmp/mongodb.log
    exit 1
fi

tail -30 /tmp/mongodb.log
