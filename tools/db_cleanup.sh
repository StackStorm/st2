#!/usr/bin/env bash
# Simple app that runs DB cleanup commands, and repopulates from disk
ROOT_PASSWORD=${MYSQL_PASSWORD:StackStorm}


echo "Cleaning MongoDB Database..."
mongo st2 --eval "db.dropDatabase();"

echo "Cleaning Mistral Database..."
SQL_QUERY="DROP DATABASE IF EXISTS mistral; \
  CREATE DATABASE mistral; \
  GRANT ALL PRIVILEGES ON mistral.* TO 'mistral'@'localhost' IDENTIFIED BY '$ROOT_PASSWORD'; \
  FLUSH PRIVILEGES;"

mysql -uroot -p$ROOT_PASSWORD -e $SQL_QUERY

cd /opt/openstack/mistral
python ./tools/sync_db.py --config-file /etc/mistral/mistral.conf

echo "Re-initializing DBs..."
st2ctl reload
