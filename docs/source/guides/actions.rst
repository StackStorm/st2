Actions
=======

To execute actions via Stanley requires the action to be registered
within Stanley. Stanley actions are composed of following:

1. Action Runner.
2. Action script.
3. Action registration.

Action Runner
^^^^^^^^^^^^^

An action runner is the execution environment for user-implemented
actions. For now Stanley comes with pre-canned Action runners like a
remote runner and shell runner which provide for user-implemented
actions to be run remotely (via SSH) and locally. The objective is to
allow the Action author to concentrate only on the implementation of the
action itself rather than setting up the environment.

Action Script
^^^^^^^^^^^^^

Action Script are user supplied content to operate against external
systems. Scripts can be shell or python and can be written assuming they
can execute on remote systems or the box/machine local to Stanley.

Action registration
^^^^^^^^^^^^^^^^^^^

Actions must be registered with Stanley in order for them to be made
available. Registration involves providing script location information
and metadata to help operate an action via various clients and API.

Writing an action
~~~~~~~~~~~~~~~~~

See
`STANLEY/contrib/examples/actions/bash\_exit\_code/bash\_exit\_code.sh <../contrib/examples/actions/bash_exit_code/bash_exit_code.sh>`__
and
`STANLEY/contrib/examples/actions/python\_fibonacci/fibonacci.py <../contrib/examples/actions/python_fibonacci/fibonacci.py>`__
to see examples of shell and python script actions respectively.

Script interpreter
^^^^^^^^^^^^^^^^^^

Action content is delivered as a script to the Stanley system. Action
scripts expect the '#!' line to identify the interpreter to run.
Currently, the Stanley system has been experimented with bash scripts
and python scripts but Stanley itself is agnostic of the interpreter so
other interpreters should work just as well. It is important to note
that all dependencies must be present on the system on which the action
is expected to execute.

Script output
^^^^^^^^^^^^^

Script must write to stdout, sterr streams and supply a useful exitcode
if applicable; these will be captured, stored and, returned via the
/actionexecutions API.

Storing the Script
^^^^^^^^^^^^^^^^^^

All actions are stored in '/opt/stackstorm/actions' on the box where
Stanley components execute. It is recommended to use the following
structure :

::

    /opt/stackstorm/actions                     # root of the actions repo
    /opt/stacktorm/actions/myaction             # root of the user supplied action
    /opt/stackstorm/actions/myaction/script.sh  # action script (.sh, .py etc.)

Note that for now the action must be contained within a single script.

Registering an action
~~~~~~~~~~~~~~~~~~~~~

Action registration can be provided as a json file stored in
'/opt/stackstorm/actions' folder on the box where Stanley components
execute.

::

    /opt/stacktorm/actions/myaction.json        # registration json

Action Definition
^^^^^^^^^^^^^^^^^

+------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Attribute              | Description                                                                                                                                                                                                                                                                                           |
+========================+=======================================================================================================================================================================================================================================================================================================+
| name                   | Name of the action.                                                                                                                                                                                                                                                                                   |
+------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| runner\_type           | The type of runner to execute the action.                                                                                                                                                                                                                                                             |
+------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| enabled                | Action cannot be invoked when disabled.                                                                                                                                                                                                                                                               |
+------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| entry\_point           | Location of the action launch script relative to the /opt/stackstorm/actions.                                                                                                                                                                                                                         |
+------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| parameters             | A dictionary of parameters and optional metadata describing type and default. The metadata is structured data following the `jsonschema <http://json-schema.org>`__ specification draft 4. If metadata is provided, input args are validated on action execution. Otherwise, validation is skipped.   |
+------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| required\_parameters   | The list of parameters that are required by the action.                                                                                                                                                                                                                                               |
+------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Example
'''''''

The following is the action definition and a table describing the
attributes.

::

    {
        "name": "http",
        "runner_type": "http-runner",
        "description": "Action that performs an http request.",
        "enabled": True,
        "entry_point":"",
        "parameters": {
            "method": {
                "enum": ["GET", "POST", "PUT", "DELETE"]
            },
            "timeout": {
                "type": "integer",
                "default": 60
            },
            "auth": {
                "type": "string"
            },
            "params": {
                "type":"string"
            }
        }
    }

Action Parameters
'''''''''''''''''

Parameter definition for the action uses jsonschema. The basic data type
that is supported are boolean, integer, number, object (json), and
string. Please review the jsonschema draft 4 for further details. On
execution of an action, the input arguments provided will be validated
against the metadata provided.

For simple data type such as string and integer, the metadata is simply
as follows. If default is provided, the value will be automatically
assigned during action execution if it is not supplied in the input
arguments.

::

    "parameters": {
        "simple1": {"type": "string"},
        "simple2": {"type": "integer", "default": 1}
    }

The corresponding command line to execute an action with this parameter
set is as follows.

::

    st2 run myaction simple1=hi simple2=3

Complex object is also supported by jsonschema. The following example
defines an input parameter that takes a JSON as input.

::

      "parameters": {
            "complex1": {
                "type": "object",
                "properties": {
                    "simple1": {"type": "string"},
                    "simple2": {"type": "integer", "default": 1}
                }
        }

For the above action, the corresponding command line to execute an
action with this parameter set is as follows.

::

    st2 run myaction complex1='{"simple1": "hi", "simple2": 3}'

Please note that an action runner may have additional parameters and how
a particular action runner handles positional args and keyword args are
different.

Picking an action runner
^^^^^^^^^^^^^^^^^^^^^^^^

The environment in which the action runs is specified by the runner.
Currently the system provides the following runners:

1. run-local : This is the local runner.
2. run-remote : This is a remote runner.
3. http-runner : This is a http runner.

Runners come with their own set of input parameters and when an action
picks a runner\_type it also inherits the runner parameters.

Specific about the runners
~~~~~~~~~~~~~~~~~~~~~~~~~~

Each runner has intrinsic behaviors which are important to understand as
an action author.

run-local runner
^^^^^^^^^^^^^^^^

The shell runner is identified by the literal 'shell'. It always
executes the action locally i.e. on the box that runs the Stanley
components under the user that runs the components.

Parameters provided by this runner are as follows:

1. 'shell' : Default value is '/usr/bin/bash' and can be overridden by
   the user when executing the action.
2. 'cmd' : All the positional arguments to be passed into the script or
   command.

run-remote runner
^^^^^^^^^^^^^^^^^

The remote runner is identified by the literal 'remote-exec-sysuser'. It
executes the actions on the boxes as defined in the host property.

Parameters provided by this runner are as follows:

1. 'hosts': Comma-separated list of hosts.
2. 'parallel': If the action should be executed in parallel on all
   hosts.
3. 'sudo': If the action should be run under sudo assuming user has
   privileges.
4. 'user': The user that runs the action. This is only used for audit
   purposes for now.
5. 'cmd': The positional args or command to be put on the shell.
6. 'remotedir': Location on the remote system where the action script
   must be copied prior to execution.

The remote runner expects a user to be specified under which to run an
action remotely on the system. As of now the user must be supplied as a
system-wide configuration and should be present on all the boxes that
run the action.

The 'ssh\_runner' section in
`STANLEY/conf/stanley.conf <../conf/stanley.conf>`__ which gets copied
over into etc/stanley/stanley.conf carries the config parameters.

1. user : name of the user; defaults to 'stanley'
2. ssh\_key\_file : location of the ssh private key whose corresponding
   public key is available on the remote boxes. If this is not provided
   than the local ssh agent must have the key for the specified user to
   exist.

Pre-define actions
~~~~~~~~~~~~~~~~~~

There are a few predefined actions that come out of the box when Stanley
is run via RPMs.

local : This action allows execution of arbitrary \*nix/shell commands
locally. Via the CLI executing this command would be -

::

    st2 run local cmd='ls -l'

remote : This action allows execution of arbitrary \*nix/shell commands
on a set of boxes. Via the CLI executing this command would be -

::

    st2 run remote cmd='ls -l' host='host1, host2' user='user1'

http : This action allows execution of http requests. Think curl
executed from the stanley box.

::

    st2 run http url="http://localhost:9101/actions" method="GET"

Action Usage
~~~~~~~~~~~~

Usage information for an action can be queried at runtime in the CLI.
The information will include additional information from the underlying
runner.

::

    st2 run <action> -h

The following is an example usage information for the included "local"
action. The list of required and optional parameters also includes those
from the "run-local" runner.

::

    ~/ $ st2 run local -h

    Action that executes an arbitrary Linux command on the localhost.

    Optional Parameters:
        cmd
            Arbitrary Linux command to be executed on the host.
            Type: string

        dir
            The working directory where the command will be executed on the host.
            Type: string

        hosts
            A comma delimited string of a list of hosts where the command will be
            executed.
            Type: string
            Default: localhost

        parallel
            If true, the command will be executed on all the hosts in parallel.
            Type: boolean

        sudo
            The command will be executed with sudo.
            Type: boolean

        user
            The user who is executing this command. This is for audit purposes
            only. The command will always execute as the user stanley.
            Type: string

