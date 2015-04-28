Actions
=======

Actions are pieces of code written in arbitrary programming language which can
perform arbitrary automation or remediation tasks in your environment.

To give you a better idea, here is a short list of tasks which can be
implemented as actions:

* restart a service on a server
* create a new cloud server
* acknowledge a Nagios / PagerDuty alert
* send a notification or alert via email or sms
* send a notification to an IRC channel
* send a message to Slack
* start a docker container
* snapshot a VM
* run nagios check

Actions can be executed when a :doc:`Rule </rules>` with a matching criteria is triggered.
Multiple Actions can be stringed together into a :doc:`Workflow </workflows>`. And each action can
be executed directly from the clients via CLI, API, or UI.

Managing and Running Actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
CLI interface provides an access to action management commands using ``st2 action <command>`` format. The list of available commands and their description can be obtained via

.. code-block:: bash

   st2 action --help

To get more information on a praticular action command, run ``st2 action <command> -h`` command. For example the following will provide help for action list command:

.. code-block:: bash

   st2 action list -h

The following commands show examples on how to obtain information on available actions and their arguments:

.. code-block:: bash

   # List all available actions (note that output may be lengthy)
   st2 action list

   # List all actions in "linux" pack
   st2 action list -p linux

   # Display information for a particular action linux.check_loadavg
   st2 action get linux.check_loadavg

   # Alternatively, use CLI's run script to obtain information on action's arguments:
   st2 run linux.check_loadavg -h

To execute an action manually, you can use ``st2 run <action with parameters>`` or ``st2 action execute <action with parameters>`` command, as shown below:

.. code-block:: bash

   # Execute action immediately and display the results
   st2 run core.http url="http://localhost:9101"

   # Schedule action execution
   st2 action execute core.http url="http://localhost:9101"
   # Obtain execution results (the command below is provided as a tip in the output of the above command):
   st2 execution get 54fc83b9e11c711106a7ae01

Action Runner
^^^^^^^^^^^^^

An action runner is the execution environment for user-implemented
actions. For now |st2| comes with pre-canned action runners like a
remote runner and shell runner which provide for user-implemented
actions to be run remotely (via SSH) and locally. The objective is to
allow the Action author to concentrate only on the implementation of the
action itself rather than setting up the environment.

Available runners
~~~~~~~~~~~~~~~~~

The environment in which the action runs is specified by the runner.
Currently the system provides the following runners:

1. ``local-script`` - This is the local runner. Actions are implemented as
   scripts. They are executed on the same hosts where |st2| components are
   running.
2. ``remote-script`` - This is a remote runner. Actions are implemented as scripts.
   They run on one or more remote hosts provided by the user.
3. ``python-script`` - This is a Python runner. Actions are implemented as Python
   classes with a ``run`` method. They run locally on the same machine where
   |st2| components are running.
4. ``http-request`` - HTTP client which performs HTTP requests for running HTTP
   actions.
5. ``action-chain`` - This runner supports executing simple linear work-flows.
   For more information, please refer to the :doc:`Workflows </workflows>`
   and :doc:`ActionChain </actionchain>` section of documentation.
6. ``mistral-v1``, ``mistral-v2`` - Those runners are built on top of the
   Mistral OpenStack project and support executing complex work-flows. For more
   information, please refer to the :doc:`Workflows </workflows>` and
   :doc:`Mistral </mistral>` section of documentation.

Runners come with their own set of input parameters and when an action
picks a runner\_type it also inherits the runner parameters.

.. _ref-actions-writing-custom:

Writing custom actions
^^^^^^^^^^^^^^^^^^^^^^

Action is composed from two parts:

1. A script file which implements the action logic
2. A YAML metadata file which describes the action

As noted above, action script can be written in an arbitrary programming
language, as long as it follows some simple conventions described below:

1. Script should exit with ``0`` status code on success and non-zero on error
   (e.g. ``1``)
2. All the log messages should be printed to standard error

Action metadata
~~~~~~~~~~~~~~~

Action metadata is used to describe the action and is defined as YAML (JSON is supported for backward
compatibility). A list
of attributes which can be present in the metadata file is included below.

* ``name`` - Name of the action.
* ``runner_type`` - The type of runner to execute the action.
* ``enabled`` - Action cannot be invoked when disabled.
* ``entry_point`` - Location of the action launch script relative to the /opt/stackstorm/packs/${pack_name}/actions/.
* ``parameters`` - A dictionary of parameters and optional metadata describing type and default. The metadata is structured data following the [jsonschema][1] specification draft 4. If metadata is provided, input args are validated on action execution. Otherwise, validation is skipped.

below you can find a sample metadata for a Python action which sends an SMS via
the Twilio web service.

.. code-block:: yaml

    ---
        name: "send_sms"
        runner_type: "python-script"
        description: "This sends a SMS using twilio."
        enabled: true
        entry_point: "send_sms.py"
        parameters:
            from_number:
                type: "string"
                description: "Your twilio 'from' number in E.164 format. Example +14151234567."
                required: true
                position: 0
            to_number:
                type: "string"
                description: "Recipient number in E.164 format. Example +14151234567."
                required: true
                position: 1
            body:
                type: "string"
                description: "Body of the message."
                required: true
                position: 2
                default: "Hello {% if system.user %} {{ system.user }} {% else %} dude {% endif %}!"


This action is using a Python runner (``python-script``), the class which
implements a ``run`` method is contained in a file called ``send_sms.py`` which
is located in the same directory as the metadata file and the action takes three
parameters (from_number, to_number, body).


Action Registration
~~~~~~~~~~~~~~~~~~~~
Once action is created 1) place it into the content location, and 2) tell the system
that the action is avalable. The actions are grouped in :doc:`packs </packs>` and located
at ``/opt/stackstorm/packs`` (default, configured, multiple locations supported).
For hacking one-off actions, the convention is to use `default` pack - just create your action in
``/opt/stackstorm/packs/default/actions``.

Register individual action by calling `st2 action create my_action_metadata.yaml`.
To reload all the action, use ``st2ctl reload --register-actions``


.. _ref-actions-converting-scripts:

Built-in Parameters
^^^^^^^^^^^^^^^^^^^

When configuring the metadata, there exists several built-in parameters that
can be used and overwritten to change the default functionality of the
various runners.

* ``args`` - (``local-shell-script``, ``remote-shell-script``) By default, |st2| will assemble
  arguments based on whether a user defines named or positional arguments.
  Adjusts the format of arguments passed to ``cmd``.
* ``cmd``  - (``local-shell-script``, ``remote-shell-script``) Configure the command to be run
  on the target system.
* ``cwd``  - (``local-shell-script``, ``remote-shell-script``) Configure the directory where
  remote commands will be executed from.
* ``env``  - (``local-shell-script``, ``local-shell-script-script``, ``remote-shell-script``,
  ``remote-shell-script-script``, ``python-script``) Environment variables which will be
  available to the executed command / script.
* ``dir``  - (``local-shell-script``, ``remote-shell-script``) Configure the directory where
  scripts are copied from a pack to the target machine prior to execution.
  Defaults to ``/tmp``.

Converting existing scripts into actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have an existing standalone script written in an arbitrary programming
or scripting language and you want to convert it to an action, the process is
very simple.

You just need to follow the steps described below:

1. Make sure the script comforms to the conventions described above
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You should make sure that the script exits with a zero status code on success
and non-zero on error. This is important since the exit code is used by |st2| to
determine if the script has finished successfully.

2. Add metadata file
~~~~~~~~~~~~~~~~~~~~

You need to add a metadata file which describes the script name, description,
entry point, which runner to use and script parameters (if any).

When converting an existing script, you will want to either use ``local-shell-script``
or ``remote-shell-script`` runner.

2. Update argument parsing in the script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

    If your script doesn't take any arguments, you can skip this step.

Local and remote script runners recognize two types of parameters:

1. ``named`` - those parameters don't include ``position`` attribute
2. ``positional`` - those parameters include ``position`` attribute

All of the parameters are passed to the script via the command-line arguments.

Named argument are passed to the script in the following format:

::

    script.sh --param1=value --param2=value --param3=value

By default, each parameter is prefixed with two dashes (``--``). If you want to
use a single dash (``-``), some other prefix or no prefix at all, you can
configure that using ``kwarg_op`` parameter in the metadata file.

For example:

.. code-block:: yaml

    ---
        name: "my_script"
        runner_type: "remote-shell-script"
        description: "Script which prints arguments to stdout."
        enabled: true
        entry_point: "script.sh"
        parameters:
            key1:
                type: "string"
                required: true
            key2:
                type: "string"
                required: true
            key3:
                type: "string"
                required: true
            kwarg_op:
                type: "string"
                immutable: true
                default: "-"

In this case, arguments are passed to the script in the following format:

::

    script.sh -key1=value1 -key2=value2 -key3=value3

And positional argument are passed to the script ordered by the ``position``
value in the following format:

::

    script.sh value2 value1 value3

If your script only uses positional arguments (which is usually the case for
a lot of scripts out there), you simply need to declare parameters with correct
value for the ``position`` attribute in the metadata file.

Example 1 - existing bash script with positional arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we have a simple bash script named ``send_to_syslog.sh`` which
writes a message provided via the command line argument to syslog.

The script takes two arguments:

1. Argument #1 is the address of the syslog server
2. Argument #2 is the message to write

.. sourcecode:: bash

    #!/usr/bin/env bash

    SERVER=$1
    MESSAGE=$2
    logger -n ${SERVER} ${MESSAGE}

Since this script is only using positional arguments, you only need to define
them in the metadata file:

.. code-block:: yaml

    ---
        name: "send_to_syslog.log"
        runner_type: "remote-shell-script"
        description: "Send a message to a provided syslog server."
        enabled: true
        entry_point: "send_to_syslog.sh"
        parameters:
            server:
                type: "string"
                description: "Address of the syslog server"
                required: true
                position: 0
            message:
                type: "string"
                description: "Message to write"
                required: true
                position: 1

As you can see above, we declare two parameters - ``server`` and ``message``.
Both of them declare a ``position`` attribute (0 for server and 1 for message),
which means they will be passed to the action script as positional arguments so
your script doesn't require any changes.

Writing custom Python actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the simplest form, Python action is a module which exposes a class which
inherits from :class:`st2actions.runners.pythonrunner.Action` and implements
a ``run`` method.

Sample Python action
~~~~~~~~~~~~~~~~~~~~

An example of a Python action that prints text provided via the
``message`` parameter to the standard output is given below.

Metadata file (``my_echo_action.yaml``):

.. code-block:: yaml

    ---
        name: "echo_action"
        runner_type: "python-script"
        description: "Print message to standard output."
        enabled: true
        entry_point: "my_echo_action.py"
        parameters:
            message:
                type: "string"
                description: "Message to print."
                required: true
                position: 0


Action script file (``my_echo_action.py``):

.. code-block:: python

    import sys

    from st2actions.runners.pythonrunner import Action

    class MyEchoAction(Action):
        def run(self, message):
            print(message)
            sys.exit(0)

As you can see above, user-supplied action parameters are passed to the ``run``
method as keyword arguments.

For a more complex example, please refer to the `actions in the Libcloud pack in
the contrib repository <https://github.com/StackStorm/st2contrib/tree/master/packs/libcloud/actions>`_.

Configuration file
~~~~~~~~~~~~~~~~~~

.. note::

    Configuration file should be used to store "static" configuration options
    which don't change between the action runs (e.g. service credentials,
    different constants, etc.).

    For options / parameters which are user defined or change often, you should
    use action parameters which are defined in the metadata file.

Python actions can store arbitrary configuration in the configuration file
which is global to the whole pack. The configuration is stored in a file
named ``config.yaml`` in a root directory of the pack.

Configuration file format is YAML. Configuration is automatically parsed and
passed to the action class constructor via the ``config`` argument.

Logging
~~~~~~~

All the logging inside the action should be performed via the logger which
is specific to this action and available via ``self.logger`` class attribute.

This logger is a standard Python logger from the ``logging`` module so all the
logger methods work as expected (e.g. ``logger.debug``, ``logger.info``, etc).

For example:

.. sourcecode:: python

    def run(self):
        ...
        success = call_some_method()

        if success:
            self.logger.info('Action successfully completed')
        else:
            self.logger.error('Action failed...')

Pre-defined actions
^^^^^^^^^^^^^^^^^^^

There are a few predefined actions that come out of the box when |st2|
is run via RPMs.

``core.local`` : This action allows execution of arbitrary \*nix/shell commands
locally. Via the CLI executing this command would be -

::

    st2 run core.local cmd='ls -l'

``core.remote`` : This action allows execution of arbitrary \*nix/shell commands
on a set of boxes. Via the CLI executing this command would be -

::

    st2 run core.remote cmd='ls -l' hosts='host1,host2' username='user1'

``core.http`` : This action allows execution of http requests. Think curl
executed from the |st2| box.

::

    st2 run core.http url="http://localhost:9101/v1/actions" method="GET"

To see other available predefined actions, run the command below.

::

    st2 action list --pack=core

Community contributed actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

More packs and actions contributed by the |st2| developers and
community can be found in the `StackStorm contrib repo on Github <https://github.com/StackStorm/st2contrib/>`_.
