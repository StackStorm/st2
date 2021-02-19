#!/usr/bin/env bash
sudo rabbitmqctl add_user stanley Ch@ngeMe
sudo rabbitmqctl delete_user guest
rabbitmqctl set_user_tags stanley administrator
rabbitmqctl set_permissions -p / stanley ".*" ".*" ".*