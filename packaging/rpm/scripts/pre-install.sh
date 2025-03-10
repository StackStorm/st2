set -e

PACKS_GROUP=%{packs_group}
SYS_USER=%{stanley_user}
ST2_USER=%{svc_user}

## Create stackstorm users and groups (differs from debian)
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
