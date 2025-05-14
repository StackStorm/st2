#!/usr/bin/env bash

# Configure RabbitMQ service inside Docker container for usage with integration
# tests on GHA

set -x
# Use custom RabbitMQ config which enables SSL / TLS listener on port 5671 with test certs
sudo cp scripts/github/rabbitmq.conf /home/runner/rabbitmq_conf/custom.conf
# The code is checked out after the container is already up, so we don't mount them.
# We copy those certs into the dir that is mounted to /bitnami/conf
sudo cp -r st2tests/st2tests/fixtures/ssl_certs /home/runner/rabbitmq_conf/
# refresh rabbitmq config - based on ENTRYPOINT logic
docker exec rabbitmq bash -c 'cat /bitnami/conf/custom.conf >> /opt/bitnami/rabbitmq/etc/rabbitmq/rabbitmq.conf'
# sleep to prevent interleaved output in GHA logs
docker exec rabbitmq cat /opt/bitnami/rabbitmq/etc/rabbitmq/rabbitmq.conf && sleep 0.1
echo
echo restarting rabbitmq container
docker restart rabbitmq
# wait for rabbitmq container to restart
# TODO: Add timeout for just in case (config error or similar)
# shellcheck disable=SC1083
until [ "$(docker inspect -f {{.State.Running}} rabbitmq)" == "true" ]; do sleep 0.1; done
echo enabled RabbitMQ plugins:
# print plugins list to: (1) ease debugging, (2) pause till rabbitmq is really running
docker exec rabbitmq rabbitmq-plugins list -e
echo
sudo wget --no-verbose http://guest:guest@localhost:15672/cli/rabbitmqadmin -O /usr/local/bin/rabbitmqadmin
sudo chmod +x /usr/local/bin/rabbitmqadmin
# print logs from stdout (RABBITMQ_LOGS=-)
docker logs --tail=100 rabbitmq
# TODO: Fail here if service fails to start and exit with -2
