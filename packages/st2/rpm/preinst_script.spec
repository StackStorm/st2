set -e

PACKS_GROUP=%{packs_group}
SYS_USER=%{stanley_user}
ST2_USER=%{svc_user}

## Permissions of directories which has to be reset on upgrade
RESET_PERMS=$(cat <<EHD | sed 's/\s\+/ /g'
ug+rw root:_packsgroup /opt/stackstorm/packs
ug+rw root:_packsgroup /opt/stackstorm/virtualenvs
755 _st2user:root      /opt/stackstorm/exports
EHD
)

## Create stackstorm users and groups (differs from debian)
create_users() {
  # create st2 user (services user)
  (id $ST2_USER 1>/dev/null 2>&1) ||
    adduser --no-create-home --system $ST2_USER

  # make st2 member of st2packs group
  (getent group $PACKS_GROUP 1>/dev/null 2>&1) || groupadd -r $PACKS_GROUP
  (groups $ST2_USER 2>/dev/null | grep -q "\b${PACKS_GROUP}\b") ||
    usermod -a -G $PACKS_GROUP $ST2_USER

  # create stanley user (unprivileged action user, we don't ship sudoers.d config)
  (id $SYS_USER 1>/dev/null 2>&1) ||
    adduser --user-group $SYS_USER
}

## Fix directories permissions on upgrade (different across maint scripts!)
#  NB! USED FOR COMPATIBILITY ON UPGRADE FROM PREVIOUS VERSIONS OF PACKAGES.
#  NB! In future package releases reseting permissions SHOULD BE REMOVED.
#
set_permissions() {
  local fileperms="$1" mode= ownership= path= current_ownership= user= group=

  echo "$fileperms" | sed -e "s/_packsgroup/$PACKS_GROUP/g" -e "s/_st2user/$ST2_USER/g" |
  while read mode ownership path; do
    user=$(echo $ownership | cut -f1 -d:)
    group=$(echo $ownership | cut -f2 -d:)
    # set top level permissions whether it's a file or directory
    [ -e $path ] || continue
    chown $ownership $path && chmod $mode $path

    # recursively change permissions of children (since those are directories)
    find $path -mindepth 1 -maxdepth 1 -not \( -user $user -group $group \) |
      xargs -I {} sh -c "chown -R $ownership {} && chmod -R $mode {}"
  done
}

create_users

# We perform upgrade (when install count > 1)
if [ "$1" -ge 1 ]; then
  set_permissions "$RESET_PERMS"
fi
