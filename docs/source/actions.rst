Actions
=======

Actions are pieces of code written in arbitrary programming language which can
perform arbitrary automation or remediation tasks in your environment.

Here is a short list of tasks which can be implemented and modeled as
StackStorm actions:

* restarting a service on a server
* starting a new server
* acknowledging a Nagios / PagerDuty alert
* sending a notification or alert via email or sms
* sending a notification to an IRC channel
* starting a docker container

Action is executed when a rule with a matching criteria is found. For more
information about the rules, please see the rules section.

Action runner
^^^^^^^^^^^^^

An action runner is the execution environment for user-implemented
actions. For now st2 comes with pre-canned action runners like a
remote runner and shell runner which provide for user-implemented
actions to be run remotely (via SSH) and locally. The objective is to
allow the Action author to concentrate only on the implementation of the
action itself rather than setting up the environment.

Aavailable runners
~~~~~~~~~~~~~~~~~~

The environment in which the action runs is specified by the runner.
Currently the system provides the following runners:

1. ``run-local`` - This is the local runner. Actions are implemented as
   scripts. They are executed on the same hosts where st2 components are
   running.
2. ``run-remote`` - This is a remote runner. Actions are implemented as scripts.
   They run on one or more remote hosts provided by the user.
3. ``run-python`` - This is a Python runner. Actions are implemented as Python
   classes with a run method. They run locally on the same machine where

Runners come with their own set of input parameters and when an action
picks a runner\_type it also inherits the runner parameters.

Writing custom actions
^^^^^^^^^^^^^^^^^^^^^^

Action is composed from two parts:

1. A script file which implements the action logic
2. A JSON metadata file which describes the action

As noted above, action script can be written in an arbitrary programming
language, as long as it follows some simple conventions described bellow:

1. Script should exit with ``0`` status code on success and ``1`` on error
2. All the log messages should be printed to standard error

Action metadata
~~~~~~~~~~~~~~~

Action metadata is used to describe the action and is defined as JSON. A list
of attributes which can be present in the metadata file is included bellow.

* ``name`` - Name of the action
* ``runner_type`` - The type of runner to execute the action.
* ``enabled`` - Action cannot be invoked when disabled.
* ``entry_point`` - Location of the action launch script relative to the /opt/stackstorm/actions.
* ``parameters`` - A dictionary of parameters and optional metadata describing type and default. The metadata is structured data following the [jsonschema][1] specification draft 4. If metadata is provided, input args are validated on action execution. Otherwise, validation is skipped.

Bellow you can find a sample metadata for a Python action which sends an SMS via
the Twilio web service.

.. code-block:: json

    {
        "name": "send_sms",
        "runner_type": "run-python",
        "description": "This sends a SMS using twilio.",
        "enabled": true,
        "entry_point": "send_sms.py",
        "parameters": {
            "from_number": {
                "type": "string",
                "description": "Your twilio 'from' number in E.164 format. Example +14151234567.",
                "required": true,
                "position": 0
            },
            "to_number": {
                "type": "string",
                "description": "Recipient number in E.164 format. Example +14151234567.",
                "required": true,
                "position": 1
            },
            "body": {
                "type": "string",
                "description": "Body of the message.",
                "required": true,
                "position": 2
            }
        }
    }

Converting existing scripts into actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have an existing standalone script written in an arbitrary programming
or scripting language and you want to convert it to an action, the process is
very simple.

You just need to follow the steps described bellow:

1. Make sure the script comforms to the conventions described above
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You should make sure that the script exists with a zero status code on success
and non-zero on error. This is important since script exit code is used to
determine if the script has finished successfully.

2. Update argument parsing in the script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO: Document how arguments are passed to the script, add examples.

3. Add metadata file
~~~~~~~~~~~~~~~~~~~~

You need to add a metadata file which describes the script name, description,
entry point, which runner to use and script parameters (if any).

When converting an existing script, you will want to either use ``run-local``
or ``run-remote`` runner.

Writing custom Python actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the simplest form, Python action is a module which exposes a class which
inherits from :class:`st2actions.runners.pythonrunner.Action` and implements
a ``run`` method.

Sample Python action
~~~~~~~~~~~~~~~~~~~~

Bellow is an example of a Python action which prints text provided via the
``message`` parameter to the standard output.

Metadata file (``my_echo_action.json``):

.. code-block:: json

    {
        "name": "echo_action",
        "runner_type": "run-python",
        "description": "Print message to standard output.",
        "enabled": true,
        "entry_point": "my_echo_action.py",
        "parameters": {
            "message": {
                "type": "string",
                "description": "Message to print.",
                "required": true,
                "position": 0
            }
        }
    }

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

There are a few predefined actions that come out of the box when st2
is run via RPMs.

``core.local`` : This action allows execution of arbitrary \*nix/shell commands
locally. Via the CLI executing this command would be -

::

    st2 run core.local cmd='ls -l'

``core.remote`` : This action allows execution of arbitrary \*nix/shell commands
on a set of boxes. Via the CLI executing this command would be -

::

    st2 run core.remote cmd='ls -l' host='host1,host2' user='user1'

``core.http`` : This action allows execution of http requests. Think curl
executed from the st2 box.

::

    st2 run core.http url="http://localhost:9101/actions" method="GET"

To see other available predefined actions, run the command bellow.

::

    st2 action list --pack=core

Community contributed actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

More packs and actions contributed by the StackStorm developers and
community can be found in the `st2 contrib repo on Github <https://github.com/StackStorm/st2contrib/>`_.
