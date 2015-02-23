#!/usr/bin/env bash
# Simple app that runs DB cleanup commands, and repopulates from disk
ROOT_PASSWORD=${MYSQL_PASSWORD:StackStorm}


echo "Cleaning MongoDB Database..."
mongo st2 --eval "db.dropDatabase();"

echo "Cleaning Mistral Database..."
mysql -uroot -p$ROOT_PASSWORD -e "DROP DATABASE IF EXISTS mistral"
mysql -uroot -p$ROOT_PASSWORD -e "CREATE DATABASE mistral"
mysql -uroot -p$ROOT_PASSWORD -e "GRANT ALL PRIVILEGES ON mistral.* TO 'mistral'@'localhost' IDENTIFIED BY '$ROOT_PASSWORD'"
mysql -uroot -p$ROOT_PASSWORD -e "FLUSH PRIVILEGES"

cd /opt/openstack/mistral
python ./tools/sync_db.py --config-file /etc/mistral/mistral.conf

echo "Re-initializing DBs..."
st2ctl reload
