#!/bin/sh
# preinst script for st2
#
# see: dh_installdeb(1)

set -e

# summary of how this script can be called:
#     <new-preinst> install
#         on fresh install
#     <new-preinst> install <old-version> <new-version>
#         on install after pkg removal without conf purge
#     <new-preinst> upgrade <old-version> <new-version>
#         on upgrade
#     <old-preinst> abort-upgrade <new-version>
#         on upgrade failed (after failure of postrm)
# https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html

PACKS_GROUP=st2packs
SYS_USER=stanley
ST2_USER=st2

## Create stackstorm users and groups (adduser differs from EL)
create_users() {
    # create st2 user (services user)
    (id $ST2_USER 1>/dev/null 2>&1) ||
        adduser --group --disabled-password --no-create-home --system $ST2_USER

    # make st2 member of st2packs group
    (getent group $PACKS_GROUP 1>/dev/null 2>&1) || groupadd -r $PACKS_GROUP
    (groups $ST2_USER 2>/dev/null | grep -q "\b${PACKS_GROUP}\b") ||
        usermod -a -G $PACKS_GROUP $ST2_USER

    # create stanley user (for actionrunner service)
    if (! id $SYS_USER 1>/dev/null 2>&1); then
        adduser --group $SYS_USER
        adduser --disabled-password --gecos "" --ingroup $SYS_USER $SYS_USER
    fi
}

case "$1" in
    install | upgrade)
        create_users
        ;;
    abort-upgrade) ;;
    *)
        # echo "preinst called with unknown argument \`$1'" >&2
        # exit 1
        ;;
esac

exit 0
