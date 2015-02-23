#!/usr/bin/env bash
# Simple app that runs DB cleanup commands, and repopulates from disk

echo "Cleaning MongoDB Database..."
mongo st2 --eval "db.dropDatabase();"

echo "Cleaning Mistral Database..."
mysql -uroot -pStackStorm -e "DROP DATABASE IF EXISTS mistral"
mysql -uroot -pStackStorm -e "CREATE DATABASE mistral"
mysql -uroot -pStackStorm -e "GRANT ALL PRIVILEGES ON mistral.* TO 'mistral'@'localhost' IDENTIFIED BY 'StackStorm'"
mysql -uroot -pStackStorm -e "FLUSH PRIVILEGES"
python ./tools/sync_db.py --config-file /etc/mistral/mistral.conf

echo "Re-initializing DBs..."
st2ctl reload
