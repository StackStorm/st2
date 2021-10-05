#!/usr/bin/env bash
# Simple app that runs DB cleanup commands, and repopulates from disk
ROOT_PASSWORD=${MYSQL_PASSWORD:StackStorm}


echo "Cleaning MongoDB Database..."
mongo st2 --eval "db.dropDatabase();"

echo "Re-initializing DBs..."
st2ctl reload
