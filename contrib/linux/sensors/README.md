## NOTICE

File watch sensor has been updated to use trigger with parameters supplied via a rule approach. Tailing a file path supplied via a config file is now deprecated.

An example rule to supply a file path is as follows:

```
---
name: sample_rule_file_watch
pack: "examples"
description: Sample rule custom trigger type - add a file to be watched by file_watch_sensor in linux pack.
enabled: false

trigger:
  parameters:
    file_path: /tmp/st2_test
  type: linux.file_watch.line

criteria: {}

action:
  parameters:
    cmd: echo "{{trigger}}"
  ref: core.local

```

Trigger ``linux.file_watch.line`` still emits the same payload as it used to.
Just the way to provide the file_path to tail has changed.
