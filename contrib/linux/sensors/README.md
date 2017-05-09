## DEPRECARTION NOTICE

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
    file_path: /var/log/dmesg
  type: linux.file_watch.file_path

criteria: {}

action:
  parameters:
    cmd: echo "{{trigger}}"
  ref: core.local

```

The new trigger emitted will have the trigger ref ``linux.file_watch.file_path``. 
Trigger ``linux.file_watch.line`` is no longer emitted.
