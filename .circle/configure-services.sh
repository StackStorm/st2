#!/bin/bash
set -e

# change into script directory
cd $(dirname `readlink -f $0`)

set -x
sudo ./configure-rabbitmq.sh
sudo ./configure-postgres.sh
