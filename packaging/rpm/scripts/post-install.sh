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

# Native .rpm specs use macros that get expanded into shell snippets.
# We are using nfpm, so we inline the macro expansion here.
# %systemd_post
#   EL8: https://github.com/systemd/systemd/blob/v239/src/core/macros.systemd.in
#   EL9: https://github.com/systemd/systemd/blob/v252/src/rpm/macros.systemd.in

if [ $1 -eq 1 ] ; then
    # Initial installation
    if [ -x "/usr/lib/systemd/systemd-update-helper" ]; then # EL 9
        /usr/lib/systemd/systemd-update-helper install-system-units ${_ST2_SERVICES} || :
    else # EL 8
        systemctl --no-reload preset ${_ST2_SERVICES} &>/dev/null || :
    fi
fi

# TODO: Maybe remove this as 'preset' (on install above) enables units by default
systemctl --no-reload enable ${_ST2_SERVICES} &>/dev/null || :

# make sure that our socket/unit generators run
if [ -x "/usr/lib/systemd/systemd-update-helper" ]; then # EL 9
    /usr/lib/systemd/systemd-update-helper system-reload || :
else # EL 8
    systemctl daemon-reload &>/dev/null || :
fi
