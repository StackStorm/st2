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

# This must include ".service" to satisfy deb-systemd-{helper,invoke}
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
# https://github.com/Debian/debhelper/blob/debian/12.10/autoscripts/postinst-systemd-enable
# https://github.com/Debian/debhelper/blob/debian/12.10/autoscripts/postinst-systemd-restart

systemd_enable() {
    # This will only remove masks created by d-s-h on package removal.
    deb-systemd-helper unmask "${1}" >/dev/null || true

    # was-enabled defaults to true, so new installations run enable.
    if deb-systemd-helper --quiet was-enabled "${1}"; then
        # Enables the unit on first installation, creates new
        # symlinks on upgrades if the unit file has changed.
        deb-systemd-helper enable "${1}" >/dev/null || true
    else
        # Update the statefile to add new symlinks (if any), which need to be
        # cleaned up on purge. Also remove old symlinks.
        deb-systemd-helper update-state "${1}" >/dev/null || true
    fi
}

if [ -n "$2" ]; then
    _dh_action=restart
else
    _dh_action=start
fi

systemd_enable_and_restart() {
    for service in "${@}"; do
        systemd_enable "${service}"
    done
    if [ -d /run/systemd/system ]; then
        systemctl --system daemon-reload >/dev/null || true
        deb-systemd-invoke $_dh_action "${@}" >/dev/null || true
    fi
}

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

case "$1" in
    configure)
        # Fail install if venv build or pack extraction fails
        rebuild_st2_venv || exit $?
        for pack in ${_ST2_PACKS}; do
            extract_st2_pack "${pack}" || exit $?
        done
        extract_st2_pack examples --target /usr/share/doc/st2/examples || :

        # shellcheck disable=SC2086
        systemd_enable_and_restart ${_ST2_SERVICES}
        ;;
    abort-upgrade | abort-remove | abort-deconfigure)
        # dh_systemd_* runs this for all actions, not just configure
        # shellcheck disable=SC2086
        systemd_enable_and_restart ${_ST2_SERVICES}
        ;;
    *)
        # echo "postinst called with unknown argument \`$1'" >&2
        # exit 1
        ;;
esac

exit 0
