#!/usr/bin/env bash

# Script which installs versions of MongoDB specified using an environment variable
if [ ! "${MONGODB_VERSION}" ]; then
    echo "MONGODB_VERSION environment variable not set."
    exit 2
fi

# Note: MongoDB 2.4 and 2.6 don't work with ramdisk since they don't work with
# small files and require at least 3 GB of space
if [ "${MONGODB_VERSION}" = '2.4.9' ] || [ "${MONGODB_VERSION}" = '2.6.12' ]; then
    DATA_DIR=/tmp/mongodbdata
else
    DATA_DIR=/mnt/ramdisk/mongodb
fi

DATA_DIR=/tmp/mongodbdata
MONGODB_DIR=/tmp/mongodb

mkdir -p ${DATA_DIR}
mkdir -p ${MONGODB_DIR}

DOWNLOAD_URL="http://fastdl.mongodb.org/linux/mongodb-linux-x86_64-${MONGODB_VERSION}.tgz"

echo "Downloading MongoDB ${MONGODB_VERSION} from ${DOWNLOAD_URL}"
wget -q ${DOWNLOAD_URL} -O /tmp/mongodb.tgz
tar -xvf /tmp/mongodb.tgz -C ${MONGODB_DIR} --strip=1

echo "Symlinking mongo shell binary to /usr/local/bin"

# Symlink latest mongodb shell
sudo ln -sf ${MONGODB_DIR}/bin/mongo /usr/local/bin/mongo
sudo ln -sf ${MONGODB_DIR}/bin/mongo /usr/bin/mongo

echo "Starting MongoDB v${MONGODB_VERSION}"
# Note: We use --notablescan option to detected missing indexes early. When this
# option is enabled, queries which result in table scan (which usually means a
# missing index or a bad query) are not allowed and result in a failed test.
#--wiredTigerStatisticsLogDelaySecs 0 --noIndexBuildRetry --noscripting --notablescan \
${MONGODB_DIR}/bin/mongod --nojournal --journalCommitInterval 500 --syncdelay 0 \
    --wiredTigerStatisticsLogDelaySecs 0 --noIndexBuildRetry --noscripting \
    --dbpath ${DATA_DIR} --bind_ip 127.0.0.1 &> /tmp/mongodb.log &
MONGODB_PID=$!

# Give process some time to start up
sleep 5

if ps -p ${MONGODB_PID} > /dev/null; then
    echo "MongoDB successfully started"
    tail -30 /tmp/mongodb.log
    exit 0
else
    echo "Failed to start MongoDB"
    tail -30 /tmp/mongodb.log
    exit 1
fi
