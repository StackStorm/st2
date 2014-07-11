#!/usr/bin/env bash

ACTION_URL=http://localhost:9101
ACTIONRUNNER_URL=http://localhost:9501

# Internal dummy
curl -i -H 'Content-Type: application/json' -X POST -d '{"name": "dummyaction", "runner_type": "internaldummy", "description": "Action that executes an arbitrary Linux command.", "enabled": true, "artifact_paths": [], "uri": null, "entry_point": "", "parameter_names": []}' ${ACTION_URL}/actions

# Internal dummy plugin
curl -i -H 'Content-Type: application/json' -X POST -d '{"name": "dummypluginaction", "runner_type": "internaldummy-plugin", "description": "Action that executes an arbitrary Linux command.", "enabled": true, "artifact_paths": [], "uri": null, "entry_point": "", "parameter_names": []}' ${ACTION_URL}/actions

# Echo action
curl -i -H 'Content-Type: application/json' -X POST -d '{"name": "echo-script", "runner_type": "shell", "description": "A echo action.", "enabled": true, "uri": null, "entry_point": "actions/bash_echo/bash_echo.sh", "artifact_paths": ["actions/bash_echo"], "parameter_names": []}' ${ACTION_URL}/actions

# Ping action
curl -i -H 'Content-Type: application/json' -X POST -d '{"name": "ping", "runner_type": "shell", "description": "A ping host action.", "enabled": true, "artifact_paths": ["actions/bash_ping"], "uri": null, "entry_point": "actions/bash_ping/bash_ping.sh", "parameter_names": ["count"]}' ${ACTION_URL}/actions

# Random exit action
curl -i -H 'Content-Type: application/json' -X POST -d '{"name": "random-exit", "runner_type": "shell", "description": "A random exit code action.", "enabled": true, "artifact_paths": ["actions/bash_exit_code"], "uri": null, "entry_point": "bash_exit_code/bash_exit_code.sh", "parameter_names": []}' ${ACTION_URL}/actions
