#!/bin/bash

if [ -f /etc/debian/version ]; then
  >&2 echo "Runners wrapper doesn't support debian platforms right now!"
  exit 1
else
  # redhatish and simply other platforms, they must support systemd
  sv=systemd
  svbin=/usr/bin/systemctl
  if [ -x $svbin ]; then
    >&2 echo "Non systemd platforms are not supported"
    exit 1
  fi
fi

WORKERSNUM=${WORKERSNUM:-`nproc`}
action="$1"; shift;
for i in `seq $WORKERSNUM`; do
  [ "$sv" = "systemd" ] && $svbin $action st2actionrunner@$i
done
