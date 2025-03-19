#!/bin/sh
# postrm script for st2
#
# see: dh_installdeb(1)

set -e

# summary of how this script can be called:
#     <postrm> remove
#         on remove or remove+purge
#     <postrm> purge
#         on purge or remove+purge
#     <old-postrm> upgrade <new-version>
#         on upgrade
#     <disappearer's-postrm> disappear <overwriter> <overwriter-version>
#         on implicit removal (all package files replaced by another package)
#     <new-postrm> abort-install
#         on failed fresh install (after <preinst> failed)
#     <new-postrm> abort-install <old-version> <new-version>
#         on failed install after pkg removal w/o conf purge (and <preinst> failed)
#     <new-postrm> failed-upgrade <old-version> <new-version>
#         on upgrade failed (after <old-postrm> failed)
#     <new-postrm> abort-upgrade <old-version> <new-version>
#         on upgrade failed (after <new-preinst> or <old-postrm> failed)
# https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html

# This must include ".service" to satisfy deb-systemd-helper
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

# Native .deb maintainer scripts are injected with debhelper snippets.
# We are using nfpm, so we inline those snippets here.
# https://github.com/Debian/debhelper/blob/debian/12.10/dh_systemd_start
# https://github.com/Debian/debhelper/blob/debian/12.10/dh_systemd_enable
# https://github.com/Debian/debhelper/blob/debian/12.10/autoscripts/postrm-systemd
# https://github.com/Debian/debhelper/blob/debian/12.10/autoscripts/postrm-systemd-reload-only

systemd_remove() {
    if [ -x "/usr/bin/deb-systemd-helper" ]; then
        deb-systemd-helper mask "${@}" >/dev/null || true
    fi
}

systemd_purge() {
    if [ -x "/usr/bin/deb-systemd-helper" ]; then
        deb-systemd-helper purge "${@}" >/dev/null || true
        deb-systemd-helper unmask "${@}" >/dev/null || true
    fi
}

systemd_reload() {
    if [ -d "/run/systemd/system" ]; then
        systemctl --system daemon-reload >/dev/null || true
    fi
}

purge_files() {
    # This -pkgsaved.disabled file might be left over from old (buggy) deb packages
    rm -f /etc/logrotate.d/st2-pkgsaved.disabled 1>/dev/null 2>&1 || :
    # Clean up other StackStorm related configs and directories
    rm -rf /etc/st2 1>/dev/null 2>&1 || :
    rm -rf /opt/stackstorm 1>/dev/null 2>&1 || :
    rm -rf /root/.st2 1>/dev/null 2>&1 || :
    rm -rf /var/log/st2 1>/dev/null 2>&1 || :
    rm -f /etc/sudoers.d/st2 1>/dev/null 2>&1 || :
}

case "$1" in
    remove)
        # shellcheck disable=SC2086
        systemd_remove ${_ST2_SERVICES}
        systemd_reload
        ;;
    purge)
        # shellcheck disable=SC2086
        systemd_purge ${_ST2_SERVICES}
        systemd_reload
        purge_files
        ;;
    upgrade | failed-upgrade | abort-install | abort-upgrade | disappear) ;;
    *)
        # echo "postrm called with unknown argument \`$1'" >&2
        # exit 1
        ;;
esac

exit 0
