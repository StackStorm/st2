#!/bin/sh

SYSTEMDCTL=/usr/bin/systemctl
UPSTARTCTL=/sbin/initctl
WORKER=st2actionrunner-worker

# 1. Choose init type
if [ -x $SYSTEMDCTL ]; then
  sv=systemd
  svbin=$SYSTEMDCTL
elif [ -x $UPSTARTCTL ]; then
  sv=upstart
  svbin=$UPSTARTCTL
else
  # Old debians, redhats and centos, amazon etc
  sv=sysv
  svbin=/etc/init.d/$WORKER
  if [ ! -x $svbin ]; then
    >&2 echo "Init file not found: $svbin"
    >&2 echo "Unknown platform, we support ONLY debian, systemd and sysv!"
    exit 1
  fi
fi

# 2. Spwan workers
WORKERSNUM=${WORKERSNUM:-`nproc`}
action="$1"; shift;
rs=0
for i in `seq $WORKERSNUM`; do
  if [ $sv = systemd ]; then
    $svbin $action st2actionrunner@$i
  elif [ $sv = upstart ]; then
    $svbin $action st2actionrunner WORKERID=$i
  elif [ $sv = sysv ]; then
    WORKERID=$i $svbin $action
  fi
  cmdrs=$?
  [ $cmdrs -gt 0 ] && rs=$cmdrs
done

exit $rs
