set -e

# This %postun scriptlet gets one argument, $1, the number of packages of
# this name that will be left on the system when this script completes. So:
#   * on upgrade:   $1 > 0
#   * on uninstall: $1 = 0
# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/#_syntax

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

# EL 8: %service_postun
if [ $1 -ge 1 ] ; then
    # Package upgrade, not uninstall
    systemctl try-restart ${_ST2_SERVICES} &>/dev/null || :
fi
# EL 9: %service_postun
if [ $1 -ge 1 ] && [ -x "/usr/lib/systemd/systemd-update-helper" ]; then
    # Package upgrade, not uninstall
    /usr/lib/systemd/systemd-update-helper mark-restart-system-units ${_ST2_SERVICES} || :
fi

# Remove st2 logrotate config, since there's no analog of apt-get purge available
if [ $1 -eq 0 ]; then
    rm -f /etc/logrotate.d/st2
fi
