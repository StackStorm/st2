set -e

_ST2_SERVICES="
st2actionrunner
st2actionrunner@
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

# EL 8: %service_preun
if [ $1 -eq 0 ] ; then
    # Package removal, not upgrade
    systemctl --no-reload disable --now ${_ST2_SERVICES} &>/dev/null || :
fi
# EL 9: %service_preun
if [ $1 -eq 0 ] && [ -x "/usr/lib/systemd/systemd-update-helper" ]; then
    # Package removal, not upgrade
    /usr/lib/systemd/systemd-update-helper remove-system-units ${_ST2_SERVICES} || :
fi
