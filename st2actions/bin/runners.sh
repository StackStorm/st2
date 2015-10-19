#!/bin/sh

SYSTEMDCTL=/usr/bin/systemctl
UPSTARTCTL=/sbin/initctl
SPAWNSVC=st2actionrunner
WORKERSVC=st2actionrunner-worker

if [ -z "$WORKERS" ]; then
  WORKERS=2
fi

# 1. Choose init type
if [ -x $SYSTEMDCTL ]; then
  sv=systemd
  svbin=$SYSTEMDCTL
elif ( /sbin/start 2>&1 | grep -q "missing job name" ); then
  sv=upstart
  svbin=$UPSTARTCTL
else
  # Old debians, redhats and centos, amazon etc
  sv=sysv
  svbin=/etc/init.d/$WORKERSVC
  if [ ! -x $svbin ]; then
    >&2 echo "Init file not found: $svbin"
    >&2 echo "Unknown platform, we support ONLY debian, systemd and sysv!"
    exit 99
  fi
fi

# 2. Spwan workers
action="$1"; shift;
rs=0
i=1
while [ $i -le $WORKERS ]; do
  if [ $sv = systemd ]; then
    $svbin $action $SPAWNSVC@$i
  elif [ $sv = upstart ]; then
    $svbin $action $WORKERSVC WORKERID=$i
  elif [ $sv = sysv ]; then
    WORKERID=$i $svbin $action
  fi
  cmdrs=$?
  [ $cmdrs -gt 0 ] && rs=$cmdrs
  i=`expr $i + 1`
done

exit $rs
