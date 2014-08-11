Actions
======

To execute actions via Stanley requires the action to be registered within Stanley. Stanley actions
are composed of following:

1. Action Runner.
2. Action script.
1. Action registration.

#### Action Runner
An action runner is the execution environment for user-implemented actions. For now Stanley comes with pre-canned Action runners like a remote runner and shell runner which provide for user-implemented actions to be run remotely (via SSH) and locally. The objective is to allow the Action author to concentrate only on the implementation of the action itself rather than setting up the environment.

#### Action Script
Action Script are user supplied content to operate against external systems. Scripts can be shell or python and can be written assuming they can execute on remote systems or the box/machine local to Stanley.

#### Action registration
Actions must be registered with Stanley in order for them to be made available. Registration involves providing script location information and metadata to help operate an action via various clients and API.

### Writing an action
See [STANLEY/contrib/examples/actions/bash_exit_code/bash_exit_code.sh](../contrib/examples/actions/bash_exit_code/bash_exit_code.sh) and [STANLEY/contrib/examples/actions/python_fibonacci/fibonacci.py](../contrib/examples/actions/python_fibonacci/fibonacci.py) to see examples of shell and python script actions respectively.

#### Script interpreter
Action content is delivered as a script to the Stanley system. Action scripts expect the '#!' line to identify the interpreter to run. Currently, the Stanley system has been experimented with bash scripts and python scripts but Stanley itself is agnostic of the interpreter so other interpreters should work just as well. It is important to note that all dependencies must be present on the system on which the action is expected to execute.

#### Script output
Script must write to stdout, sterr streams and supply a useful exitcode if applicable; these will be captured, stored and, returned via the /actionexecutions API.

#### Storing the Script
All actions are stored in '/opt/stackstorm/actions' on the box where Stanley components execute. It is recommended to use the following structure :

    /opt/stackstorm/actions                     # root of the actions repo
    /opt/stacktorm/actions/myaction             # root of the user supplied action
    /opt/stackstorm/actions/myaction/script.sh  # action script (.sh, .py etc.)

Note that for now the action must be contained within a single script.

### Registering an action
Action registration can be provided as a json file stored in '/opt/stackstorm/actions' folder on the box where Stanley components execute.

    /opt/stacktorm/actions/myaction.json        # registration json

#### Schema
    {
        "name": "local",         # name of the action.
        "runner_type": "shell",  # name of the runner.
        "description": "",       # description of the action.
        "enabled": true,         # If this action is enabled. A disabled action will not execute until it is enabled.
        "entry_point": "",       # Location of the script relative to '/opt/stackstorm/actions'
        "parameters": {}         # The parameter of the action. These are passed down as key-value arg on the command line.
    }

#### Picking an action runner
The environment in which the action runs is specified by the runner. Currently the system provides the following runners:

1. shell : This is the local runner.
2. remote-exec-sysuser : This is a remote runner.

Runners come with their own set of input parameters and when an action picks a runner_type it also inherits the runner parameters.

### Specific about the runners
Each runner has intrinsic behaviors which are important to understand as an action author.

#### shell runner
The shell runner is identified by the literal 'shell'. It always executes the action locally i.e. on the box that runs the Stanley components under the user that runs the components.

Parameters provided by this runner are as follows:

1. 'shell' : Default value is '/usr/bin/bash' and can be overridden by the user when executing the action.
2. 'cmd' : All the positional arguments to be passed into the script or command.

#### remote runner
The remote runner is identified by the literal 'remote-exec-sysuser'. It executes the actions on the boxes as defined in the host property.

Parameters provided by this runner are as follows:

1. 'hosts': Comma-separated list of hosts.
2. 'parallel': If the action should be executed in parallel on all hosts.
1. 'sudo': If the action should be run under sudo assuming user has privileges.
1. 'user': The user that runs the action. This is only used for audit purposes for now.
1. 'cmd': The positional args or command to be put on the shell.
1. 'remotedir': Location on the remote system where the action script must be copied prior to execution.

The remote runner expects a user to be specified under which to run an action remotely on the system. As of now the user must be supplied as a system-wide configuration and should be present on all the boxes that run the action.

The 'fabric_runner' section in [STANLEY/conf/stanley.conf](../conf/stanley.conf) which gets copied over into etc/stanley/stanley.conf carries the config parameters.

1. user : name of the user; defaults to 'stanley'
2. ssh_key_file : location of the ssh private key whose corresponding public key is available on the remote boxes. If this is not provided than the local ssh agent must have the key for the specified user to exist.

### Pre-define actions
There are a few predefined actions that come out of the box when Stanley is run via RPMs.

local : This action allows execution of arbitrary *nix/shell commands locally. Via the CLI executing this command would be -

    st2 run local cmd='ls -l'

remote : This action allows execution of arbitrary *nix/shell commands on a set of boxes. Via the CLI executing this command would be -

    st2 run remote cmd='ls -l' host='host1, host2' user='user1'
