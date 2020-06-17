#!/bin/sh

# Default number of workers
WORKERS="${WORKERS:-10}"

# Choose init system to perform actions with a service.
choose_sysinit() {
  local service="$1" svinit="sysv"
  if [ -d /run/systemd/system ]; then
    svinit=systemd
  else
    if [ ! -x /etc/init.d/${service} ]; then
      >&2 echo "Supported init systems: systemd and sysv"
      >&2 echo "/etc/init.d/${service} not found or disabled"
      exit 99
    fi
  fi
  echo $svinit
}

# Perform service action over the given number of workers.
spawn_workers() {
  local action=$1 init= seq=
  seq=$(bash -c "printf '%g\\n' {1..$WORKERS}")

  # Choose init system and exit if it's not supported.
  init=$(choose_sysinit st2actionrunner)
  [ $? -gt 0 ] && exit $?

  case $init in
    systemd)
      echo "$seq" | xargs -I{} /bin/systemctl $action \
          st2actionrunner@{}
      ;;
    sysv)
      echo "$seq" | xargs -I{} /bin/sh -c \
          "WORKERID={} /etc/init.d/st2actionrunner-worker $action"
      ;;
  esac
  # return 1 in case if xargs failed any invoked commands.
  retval=$?; [ $retval -ge 123 ] && return 1 || return $retval
}

# Perform service action on all actionrunners
if [ -z "$1" ]; then
  echo >&2 "Usage: $0 action"
  exit 99
fi

spawn_workers $1
