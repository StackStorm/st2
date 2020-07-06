#!/bin/sh

LSB_RELEASE=$(which lsb_release)
SYSTEMDCTL=/bin/systemctl
UPSTARTCTL=/sbin/initctl
SPAWNSVC=st2actionrunner
WORKERSVC=st2actionrunner-worker

# Set default number of workers
if [ -z "$WORKERS" ]; then
  WORKERS=$(/usr/bin/nproc 2>/dev/null)
  WORKERS="${WORKERS:-4}"
fi

# 1. Choose init type
if [ -z "$sv" -a -x $SYSTEMDCTL ]; then
  sv=systemd
  svbin=$SYSTEMDCTL
elif [ -z "$sv" ] && ( /sbin/start 2>&1 | grep -q "missing job name" ); then
  sv=upstart
  svbin=$UPSTARTCTL
else
  >&2 echo "Unknown platform, we support ONLY upstart and systemd!"
  exit 99
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
  fi
  cmdrs=$?
  [ $cmdrs -gt 0 ] && rs=$cmdrs
  i=`expr $i + 1`
done

exit $rs
