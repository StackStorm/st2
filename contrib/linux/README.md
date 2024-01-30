# Linux Integration Pack

This pack contains actions for commonly used Linux commands and tools.

## Sensors

### FileWatchSensor

This sensor monitors specified files for new new lines. Once a new line is
detected, a trigger is emitted.

### linux.file_watch.line trigger

Example trigger payload:

```json
{
    "file_path": "/var/log/auth.log",
    "file_name": "auth.log",
    "line": "Jan 18 13:38:15 vagrant-ubuntu-trusty-64 sudo:  vagrant : TTY=pts/3 ; PWD=/data/stanley ; USER=root ; COMMAND=/bin/ls"
}
```

## Actions

* ``vmstat`` - Wrapper around the `vmstat` command.
* ``rsync`` - Wrapper around the `rsync` command.
* ``netstat`` - Wrapper around the `netstat` command.
* ``lsof`` - Wrapper around the `lsof` command.
* ``service`` - Action which allows you to perform an action (start, stop,
  restart, etc.) on a system service. Currently it supports the following
  distributions: Ubuntu / Debian (upstart, sys init), RedHat / Fedora
  (systemd).
* ``touch`` - Action which touches a file.
* ``check_loadavg`` - Action which retrieves load average from a remote host.
* ``check_processes`` - Action which retrieves useful information about
  matching process on a remote host.
* ``dig`` - Python wrapper for dig command. Requires ``bind-utils`` rpm or ``dnsutils`` deb installed.

## Troubleshooting

* On CentOS7/RHEL7, dig is not installed by default. Run ``sudo yum install bind-utils`` to install.
* On CentOS8/RHEL8, lsof is not installed by default. Run ``sudo yum install lsof`` to install.
