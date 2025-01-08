set -e

# This %post scriptlet gets one argument, $1, the number of packages of
# this name that will be left on the system when this script completes. So:
#   * on install: $1 = 1
#   * on upgrade: $1 > 1
# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/#_syntax

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

# EL 8: %service_post
if [ $1 -eq 1 ] ; then
    # Initial installation
    systemctl --no-reload preset ${_ST2_SERVICES} &>/dev/null || :
fi
# EL 9: %service_post
if [ $1 -eq 1 ] && [ -x "/usr/lib/systemd/systemd-update-helper" ]; then
    # Initial installation
    /usr/lib/systemd/systemd-update-helper install-system-units ${_ST2_SERVICES} || :
fi

systemctl --no-reload enable ${_ST2_SERVICES} &>/dev/null || :

# make sure that our socket generators run
systemctl daemon-reload &>/dev/null || :
