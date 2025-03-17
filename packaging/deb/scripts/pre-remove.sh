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

# This must include ".service" to satisfy deb-systemd-invoke
_ST2_SERVICES="
st2actionrunner.service
st2api.service
st2auth.service
st2garbagecollector.service
st2notifier.service
st2rulesengine.service
st2scheduler.service
st2sensorcontainer.service
st2stream.service
st2timersengine.service
st2workflowengine.service
"

# based on dh_systemd_start/12.10ubuntu1
if [ -d /run/systemd/system ] && [ "$1" = remove ]; then
    systemctl stop ${_ST2_SERVICES} >/dev/null || true
fi
