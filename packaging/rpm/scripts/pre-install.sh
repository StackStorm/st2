#!/bin/bash
set -e

# This %pre scriptlet gets one argument, $1, the number of packages of
# this name that will be left on the system when this script completes. So:
#   * on install: $1 = 1
#   * on upgrade: $1 > 1
# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/#_syntax

PACKS_GROUP=st2packs
SYS_USER=stanley
ST2_USER=st2

## Create stackstorm users and groups (adduser differs from debian)
create_users() {
    # create st2 user (services user)
    (id $ST2_USER 1>/dev/null 2>&1) ||
        adduser --no-create-home --system --user-group $ST2_USER

    # make st2 member of st2packs group
    (getent group $PACKS_GROUP 1>/dev/null 2>&1) || groupadd -r $PACKS_GROUP
    (groups $ST2_USER 2>/dev/null | grep -q "\b${PACKS_GROUP}\b") ||
        usermod -a -G $PACKS_GROUP $ST2_USER

    # create stanley user (unprivileged action user, we don't ship sudoers.d config)
    (id $SYS_USER 1>/dev/null 2>&1) ||
        adduser --user-group $SYS_USER
}

create_users
