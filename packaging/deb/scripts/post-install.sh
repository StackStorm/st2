#!/bin/sh
# postinst script for st2
#
# see: dh_installdeb(1)

set -e

# summary of how this script can be called:
#     <new-postinst> configure
#         on fresh install
#     <new-postinst> configure <most-recently-configured-version>
#         on upgrade OR on install after pkg removal without purging conf files
#     <old-postinst> abort-upgrade <new version>
#         on upgrade failed (after failure of prerm, preinst, postrm)
#     <conflictor's-postinst> abort-remove in-favour <package> <new-version>
#         on removal due to conflict with other package
#     <postinst> abort-remove
#         on removal (after failure of prerm)
#     <deconfigured's-postinst> abort-deconfigure in-favour
#             <failed-install-package> <version>
#             [ removing <conflicting-package> <version> ]
#         on removal due to breaks/conflict with other package (if --auto-deconfigure)
#     <postinst> triggered <trigger-name> [<trigger-name> ...]
#         when a trigger we've registered interest in fires,
#         such as when /usr/bin/python3.9 (or similar) gets updated,
#         allowing this script to rebuild the venv.
# https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html
# https://www.mankier.com/5/deb-postinst
# https://www.mankier.com/5/deb-triggers
# https://stackoverflow.com/questions/15276535/dpkg-how-to-use-trigger

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

case "$1" in
    configure)
        # make sure that our socket generators run
        systemctl daemon-reload >/dev/null 2>&1 || true
    ;;
    abort-upgrade|abort-remove|abort-deconfigure)
    ;;
    *)
        # echo "postinst called with unknown argument \`$1'" >&2
        # exit 1
    ;;
esac

# based on dh_systemd_enable/12.10ubuntu1 and dh_systemd_start/12.10ubuntu1
if [ "$1" = "configure" ] || [ "$1" = "abort-upgrade" ] || [ "$1" = "abort-deconfigure" ] || [ "$1" = "abort-remove" ] ; then
    for service in ${_ST2_SERVICES}; do
        # This will only remove masks created by d-s-h on package removal.
        deb-systemd-helper unmask "${service}" >/dev/null || true

        # was-enabled defaults to true, so new installations run enable.
        if deb-systemd-helper --quiet was-enabled "${service}"; then
            # Enables the unit on first installation, creates new
            # symlinks on upgrades if the unit file has changed.
            deb-systemd-helper enable "${service}" >/dev/null || true
        else
            # Update the statefile to add new symlinks (if any), which need to be
            # cleaned up on purge. Also remove old symlinks.
            deb-systemd-helper update-state "${service}" >/dev/null || true
        fi
    done
    systemctl --system daemon-reload >/dev/null || true
		if [ -n "$2" ]; then
        _dh_action=restart
		else
        _dh_action=start
		fi
		deb-systemd-invoke $_dh_action ${_ST2_SERVICES} >/dev/null || true
fi

exit 0
