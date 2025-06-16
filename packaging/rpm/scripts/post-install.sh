#!/bin/bash
set -e

# This %post scriptlet gets one argument, $1, the number of packages of
# this name that will be left on the system when this script completes. So:
#   * on install: $1 = 1
#   * on upgrade: $1 > 1
# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/#_syntax

# The supported minor versions of python3 (python3.{minor}) in reverse order.
_ST2_PY3_MINOR="11 10 9 8"

# The default set of packs installed with st2.
_ST2_PACKS="
chatops
core
default
linux
packs
"

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

rebuild_st2_venv() {
    _pex="/opt/stackstorm/install/st2.pex"
    if [ ! -e "${_pex}" ]; then
        # symlink does not exist or does not point to a valid file
        # (the symlink target might not exist any more if upgrading
        # to an st2 version that drops support for an older python)
        rm -f "${_pex}"
        for minor in ${_ST2_PY3_MINOR}; do
            if [ -x "/usr/bin/python3.${minor}" ]; then
                ln -s "st2-py3${minor}.pex" "${_pex}"
                break
            fi
        done
        if [ ! -e "${_pex}" ]; then
            # symlink creation failed; the python dep is somehow missing
            return 42
        fi
    fi
    "${_pex}"
}

extract_st2_pack() {
    pack=${1}
    shift
    # shellcheck disable=SC2209
    PAGER=cat /opt/stackstorm/install/packs/"${pack}".tgz.run --quiet --accept "${@}"
}

# Fail install if venv build or pack extraction fails
rebuild_st2_venv || exit $?
for pack in ${_ST2_PACKS}; do
    extract_st2_pack "${pack}" || exit $?
done
extract_st2_pack examples --target /usr/share/doc/st2/examples || :

# Native .rpm specs use macros that get expanded into shell snippets.
# We are using nfpm, so we inline the macro expansion here.
# %systemd_post
#   EL8: https://github.com/systemd/systemd/blob/v239/src/core/macros.systemd.in
#   EL9: https://github.com/systemd/systemd/blob/v252/src/rpm/macros.systemd.in

if [ "$1" -eq 1 ]; then
    # Initial installation
    if [ -x "/usr/lib/systemd/systemd-update-helper" ]; then # EL 9
        # shellcheck disable=SC2086
        /usr/lib/systemd/systemd-update-helper install-system-units ${_ST2_SERVICES} || :
    else # EL 8
        # shellcheck disable=SC2086
        systemctl --no-reload preset ${_ST2_SERVICES} &>/dev/null || :
    fi
fi

# shellcheck disable=SC2086
# TODO: Maybe remove this as 'preset' (on install above) enables units by default
systemctl --no-reload enable ${_ST2_SERVICES} &>/dev/null || :

# make sure that our socket/unit generators run
if [ -x "/usr/lib/systemd/systemd-update-helper" ]; then # EL 9
    /usr/lib/systemd/systemd-update-helper system-reload || :
else # EL 8
    systemctl daemon-reload &>/dev/null || :
fi
