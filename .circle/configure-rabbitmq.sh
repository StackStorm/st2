#!/bin/bash

# Enable remote guest access
CONFIG=$(cat <<EHD
[{rabbit, [{disk_free_limit, 10}, {loopback_users, []}, {tcp_listeners, [{"0.0.0.0", 5672}]}]}].
EHD
)

service rabbitmq-server stop
echo "$CONFIG" > /etc/rabbitmq/rabbitmq.config
service rabbitmq-server start
