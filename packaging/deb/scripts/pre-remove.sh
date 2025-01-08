#!/bin/sh
# prerm script for st2

set -e

# summary of how this script can be called:
#     <new-prerm> remove
#         on remove or remove+purge
#     <old-prerm> upgrade <new-version>
#         on upgrade
#     <conflictor's-prerm> remove in-favour <package> <new-version>
#         on removal due to conflict with other package
#     <deconfigured's-prerm> deconfigure in-favour
#             <package-being-installed> <version>
#             [ removing <conflicting-package> <version> ]
#         on removal due to breaks/conflict with other package (if --auto-deconfigure)
#     <new-prerm> failed-upgrade <old-version> <new-version>
#         on upgrade failed (after <old-prerm> failed)
# https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html

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
