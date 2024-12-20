#!/bin/sh
# prerm script for st2

set -e

_ST2_SERVICES="
st2actionrunner
st2api
st2auth
st2garbagecollector
st2notifier
st2rulesengine
st2scheduler
st2sensorcontainer
st2stream
st2timersengine
st2workflowengine
"

# based on dh_systemd_start/12.10ubuntu1
if [ -d /run/systemd/system ] && [ "$1" = remove ]; then
    systemctl stop ${_ST2_SERVICES} >/dev/null || true
fi
