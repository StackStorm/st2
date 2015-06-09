StackStorm CLI 101
==================

StackStorm command line client (CLI) allows you talk to and operate StackStorm
deployment using the command line interface. It talks to the StackStorm
installation using the public API.

Installation
------------

If you installed StackStorm using packages or a deployment script, the CLI
should already be available. On the other hand, if you used the run from
sources method, see :ref:`setup-st2-cli` section for information how to
install and set up the client.

.. _cli-configuration:

Configuration
-------------

The command line client can be configured using one or a mix of approaches
listed below.

* Configuration file (``~/.st2/config``)
* Environment variables (``ST2_API_URL``, etc.)
* Command line arguments (``st2 --cacert=... action list``, etc.)

Approaches have the following precedence from the higest to the lowests:
command line arguments, environment variables, configuration file. This means
that the values specified as command line arguments have the higest precedence
and the values specified in the configuration file have the lowest precedence.

If the same value is specified in multiple places, the value with the higest
precedence will be used. For example, if api url is specified in the
configuration file and inside the environment variable, value from the
environment variable will be used.

Configuration file
~~~~~~~~~~~~~~~~~~

The CLI can be configure through an ini-style configuration file which is by
default located at ``~/.st2/config``.

If you want to use configuration from a different file (e.g. you have one
config per deployment or environment) you can select which file to use using
``ST2_CONFIG_FILE`` environment variable or ``--config-file`` command line
argument.

For example (environment variable):

.. sourcecode:: bash

    ST2_CONFIG_FILE=~/.st2/prod-config st2 action list

For example (command line argument):

.. sourcecode:: bash

    st2 --config-file=~/.st2/prod-config action list

An example configuration file with all the options and the corresponding
explanation is included below.

.. literalinclude:: ../../conf/st2rc.sample.ini
    :language: ini

If you want the CLI to skip parsing of the configuration file, you can do that
by passing ``--skip-config`` flag to the CLI as shown below:

.. sourcecode:: bash

    st2 --skip-config action list

.. _cli-auth-token-caching:

Authentication and auth token caching
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you specify authentication credentials in the configuration file, the CLI
will try to use those credentials to authenticate and retrieve an auth token.

This auth token is by default cached on the local filesystem (``~/.st2/token``
file``) and re-used on the subsequent requests to the API service.

If you want to disable auth token caching and want the CLI to retrieve a new
auth token on each invocation, you can do that by setting ``cache_token``
option to ``False``.

.. sourcecode:: ini

    [cli]
    cache_token = False

CLI will by default also try to retrieve a new token if an existing one has
expired.

If you have manually deleted or revoked a token before the expiration you can
clean the token cached by the CLI by removing ``~/.st2/token`` file.

Using debug mode
----------------

The command line tools accepts ``--debug`` flag. When this flag is provided,
debug mode will be enabled. Debug mode consists of the following:

* On error / exception, full stack trace and client settings (api url, auth
  url, proxy information, etc.) are printed to the console.
* Curl command for each request is printed to the console. This makes it easy
  to reproduce actions performed by the CLI using curl.
* Raw API responses are printed to the console.

For example:

.. sourcecode:: bash

    st2 --debug action list --pack=core

Example output (no error):

.. sourcecode:: bash

    st2 --debug action list --pack=core
    # -------- begin 140702450464272 request ----------
    curl -X GET -H  'Connection: keep-alive' -H  'Accept-Encoding: gzip, deflate' -H  'Accept: */*' -H  'User-Agent: python-requests/2.5.1 CPython/2.7.6 Linux/3.13.0-36-generic' 'http://localhost:9101/v1/actions?pack=core'
    # -------- begin 140702450464272 response ----------
    [
        {
            "runner_type": "http-runner",
            "name": "http",
            "parameters": {
            ...

Example output (error):

.. sourcecode:: bash

    st2 --debug action list --pack=core
    ERROR: ('Connection aborted.', error(111, 'Connection refused'))

    Client settings:
    ----------------
    ST2_BASE_URL: http://localhost
    ST2_AUTH_URL: https://localhost:9100
    ST2_API_URL: http://localhost:9101/v1

    Proxy settings:
    ---------------
    HTTP_PROXY:
    HTTPS_PROXY:

    Traceback (most recent call last):
      File "./st2client/st2client/shell.py", line 175, in run
        args.func(args)
      File "/data/stanley/st2client/st2client/commands/resource.py", line 218, in run_and_print
        instances = self.run(args, **kwargs)
      File "/data/stanley/st2client/st2client/commands/resource.py", line 37, in decorate
        return func(*args, **kwargs)
        ...

Using CLI inside scripts
------------------------

CLI returns a non-zero return code for any erroneous operation. You can capture
the return code of CLI commands to check whether the command succeeded.

For example:

.. sourcecode:: bash

    st2 action get twilio.send_sms

    +-------------+--------------------------------------------------------------+
    | Property    | Value                                                        |
    +-------------+--------------------------------------------------------------+
    | id          | 54bfff490640fd2f6224ac1a                                     |
    | ref         | twilio.send_sms                                              |
    | pack        | twilio                                                       |
    | name        | send_sms

Now, let's get the exit code of the previous command.

.. sourcecode:: bash

    echo $?

    0

Now, let's run a command that we know will fail.

.. sourcecode:: bash

    st2 action get twilio.make_call

    Action "twilio.make_call" is not found.

Let's check the exit code of the last command.

.. sourcecode:: bash

    echo $?

    2

Obtaining authentication token inside scripts
---------------------------------------------

If you want to authenticate and obtain an authentication token inside your
(shell) scripts, you can use `st2 auth` CLI command in combination with ``-t``
flag to do that.

This flag will cause the command to only print the token to the stdout on
successful authentication - this means you don't need to deal with parsing
JSON or CLI output format.

Example command usage:

.. sourcecode:: bash

    st2 auth test1 -p testpassword -t

    0280826688c74bb9bd541c26631df298

Example usage inside a bash script:

.. sourcecode:: bash

    TOKEN=$(st2 auth test1 -p testpassword -t)

    # Now you can use the token (e.g. pass it to other commands, set an
    # environment variable, etc.)
    echo ${TOKEN}

Changing the CLI output format
------------------------------

By default, CLI returns and prints results in a user-friendly table oriented
format.

For example:

.. sourcecode:: bash

    st2 action list --pack=slack

    +--------------------+-------+--------------+-------------------------------+
    | ref                | pack  | name         | description                   |
    +--------------------+-------+--------------+-------------------------------+
    | slack.post_message | slack | post_message | Post a message to the Slack   |
    |                    |       |              | channel.                      |
    +--------------------+-------+--------------+-------------------------------+

If you want a raw JSON result as returned by the API (e.g. you are calling CLI
as part of your script and you want raw result which you can parse), you can
pass ``-j`` flag to the command.

For example:

.. sourcecode:: bash

    st2 action list -j --pack=slack

    [
        {
            "description": "Post a message to the Slack channel.",
            "name": "post_message",
            "pack": "slack",
            "ref": "slack.post_message"
        }
    ]

Only displaying a particular attribute when retrieving action result
--------------------------------------------------------------------

By default when retrieving action execution result using ``execution get``
command, the whole result object will be printed.

For example:

.. sourcecode:: bash

    st2 execution get 54d8c52e0640fd1c87b9443f

    STATUS: succeeded
    RESULT:
    {
        "failed": false,
        "stderr": "",
        "return_code": 0,
        "succeeded": true,
        "stdout": "Mon Feb  9 14:33:18 UTC 2015
    "
    }

If you only want to retrieve and print out a specified attribute, you can do
that using ``-k <attribute name>`` flag.

For example, if you only want to print ``stdout`` attribute of the result
object:

.. sourcecode:: bash

    st2 execution get -k stdout 54d8c52e0640fd1c87b9443f

    Mon Feb  9 14:33:18 UTC 2015

If you only want to retrieve and print out a specified attribute of the execution,
you can do that using ``--attr <attribute name>`` flag.

For example, if you only want to print ``start_timestamp`` attribute of the result
object:

.. sourcecode:: bash

    st2 execution get 54d8c52e0640fd1c87b9443f -a start_timestamp

    start_timestamp: 2015-02-24T23:01:15.088293Z

And you can also specify multiple attributes:

.. sourcecode:: bash

    st2 execution get 54d8c52e0640fd1c87b9443f --attr status result.stdout result.stderr

    status: succeeded
    result.stdout: Mon Feb  9 14:33:18 UTC 2015

    result.stderr:

Same goes for the ``execution list`` command:

.. sourcecode:: bash

    st2 execution list -a id status result

    +--------------------------+-----------+---------------------------------+
    | id                       | status    | result                          |
    +--------------------------+-----------+---------------------------------+
    | 54eb51000640fd34e0a9a2ce | succeeded | {u'succeeded': True, u'failed': |
    |                          |           | False, u'return_code': 0,       |
    |                          |           | u'stderr': u'', u'stdout':      |
    |                          |           | u'2015-02-23                    |
    |                          |           | 16:10:39.916375\n'}             |
    | 54eb51000640fd34e0a9a2d2 | succeeded | {u'succeeded': True, u'failed': |
    |                          |           | False, u'return_code': 0,       |
    |                          |           | u'stderr': u'', u'stdout':      |
    |                          |           | u'2015-02-23                    |
    |                          |           | 16:10:40.444848\n'}             |


Escaping shell variables when using core.local and core.remote actions
----------------------------------------------------------------------

When you use local and remote actions (e.g. ``core.local``, ``core.remote``,
etc.), you need to wrap ``cmd`` parameter value in a single quote or escape the
variables, otherwise the shell variables will be expanded locally which is
something you usually don't want.

Example (using single quotes):

.. sourcecode:: bash

    st2 run core.local env='{"key1": "val1", "key2": "val2"}' cmd='echo "ponies ${key1} ${key2}"'

Example (escaping the variables):

.. sourcecode:: bash

    st2 run core.remote hosts=localhost env='{"key1": "val1", "key2": "val2"}' cmd="echo ponies \${key1} \${key2}

Specifying parameters which type is "array"
--------------------------------------------

When running an action using ``st2 run`` command, you specify value of
parameters which type is ``array`` as a comma delimited string.

Inside the CLI, this string gets split on comma and passed to the API as a
list.

For example:

.. sourcecode:: bash

    st2 run mypack.myaction parametername="value 1,value2,value3"

In this case, ``parametername`` value would get passed to the API as
a list (JSON array) with three items - ``["value 1", "value2", "value3"]``.

Specifying parameters which type is "object"
--------------------------------------------

When running an action using ``st2 run`` command, you can specify value of
parameters which type is ``object`` using two different approaches:

1. Using JSON

For complex objects, you should use JSON notation. For example:

.. sourcecode:: bash

    st2 run core.remote hosts=localhost env='{"key1": "val1", "key2": "val2"}' cmd="echo ponies \${key1} \${key2}

2. Using a string of comma-delimited ``key=value`` pairs

For simple objects (such as specifying a dictionary where both keys and values
are simple strings), you should use this notation.

.. sourcecode:: bash

    st2 run core.remote hosts=localhost env="key1=val1,key2=val2" cmd="echo ponies \${key1} \${key2}"

Reading parameter value from a file
-----------------------------------

CLI also supports special ``@parameter`` notation which makes it read parameter
value from a file.

An example of when this might be useful is when you are using a http runner
actions or when you want to read information such a private SSH key content
from a file.

Example:

.. sourcecode:: bash

    st2 run core.remote hosts=<host> username=<username> @private_key=/home/myuser/.ssh/id_rsa cmd=<cmd>

Re-running an action
--------------------

To re-run a particular action, you can use the ``execution re-run <existing
execution id>`` command.

By default, this command re-runs an action with the same set of input parameters
which were used with the original action.

The command takes the same arguments as the ``run`` / ``action execute``
command. This means you can pass additional runner or action specific parameters
to the command. Those parameters are then merged with the parameters from the
original action and used to run a new action.

For example:

.. sourcecode:: bash

    st2 run core.local env="VAR=hello" cmd='echo $VAR; date'
    .
    +-----------------+--------------------------------+
    | Property        | Value                          |
    +-----------------+--------------------------------+
    | id              | 54e37a3c0640fd0bd07b1930       |
    | context         | {                              |
    |                 |     "user": "stanley"          |
    |                 | }                              |
    | parameters      | {                              |
    |                 |     "cmd": "echo $VAR; date",  |
    |                 |     "env": {                   |
    |                 |         "VAR": "hello"         |
    |                 |     }                          |
    |                 | }                              |
    | status          | succeeded                      |
    | start_timestamp | Tue, 17 Feb 2015 17:28:28 UTC  |
    | result          | {                              |
    |                 |     "failed": false,           |
    |                 |     "stderr": "",              |
    |                 |     "return_code": 0,          |
    |                 |     "succeeded": true,         |
    |                 |     "stdout": "hello           |
    |                 | Tue Feb 17 17:28:28 UTC 2015   |
    |                 | "                              |
    |                 | }                              |
    | action          | core.local                     |
    | callback        |                                |
    | end_timestamp   | Tue, 17 Feb 2015 17:28:28 UTC  |
    +-----------------+--------------------------------+

    st2 run re-run 54e37a3c0640fd0bd07b1930
    .
    +-----------------+--------------------------------+
    | Property        | Value                          |
    +-----------------+--------------------------------+
    | id              | 54e37a630640fd0bd07b1932       |
    | context         | {                              |
    |                 |     "user": "stanley"          |
    |                 | }                              |
    | parameters      | {                              |
    |                 |     "cmd": "echo $VAR; date",  |
    |                 |     "env": {                   |
    |                 |         "VAR": "hello"         |
    |                 |     }                          |
    |                 | }                              |
    | status          | succeeded                      |
    | start_timestamp | Tue, 17 Feb 2015 17:29:07 UTC  |
    | result          | {                              |
    |                 |     "failed": false,           |
    |                 |     "stderr": "",              |
    |                 |     "return_code": 0,          |
    |                 |     "succeeded": true,         |
    |                 |     "stdout": "hello           |
    |                 | Tue Feb 17 17:29:07 UTC 2015   |
    |                 | "                              |
    |                 | }                              |
    | action          | core.local                     |
    | callback        |                                |
    | end_timestamp   | Tue, 17 Feb 2015 17:29:07 UTC  |
    +-----------------+--------------------------------+

    st2 run re-run 7a3c0640fd0bd07b1930 env="VAR=world"
    .
    +-----------------+--------------------------------+
    | Property        | Value                          |
    +-----------------+--------------------------------+
    | id              | 54e3a8f50640fd140ae20af7       |
    | context         | {                              |
    |                 |     "user": "stanley"          |
    |                 | }                              |
    | parameters      | {                              |
    |                 |     "cmd": "echo $VAR; date",  |
    |                 |     "env": {                   |
    |                 |         "VAR": "world"         |
    |                 |     }                          |
    |                 | }                              |
    | status          | succeeded                      |
    | start_timestamp | Tue, 17 Feb 2015 20:47:49 UTC  |
    | result          | {                              |
    |                 |     "failed": false,           |
    |                 |     "stderr": "",              |
    |                 |     "return_code": 0,          |
    |                 |     "succeeded": true,         |
    |                 |     "stdout": "world           |
    |                 | Tue Feb 17 20:47:49 UTC 2015   |
    |                 | "                              |
    |                 | }                              |
    | action          | core.local                     |
    | callback        |                                |
    | end_timestamp   | Tue, 17 Feb 2015 20:47:49 UTC  |
    +-----------------+--------------------------------+

Cancel an execution
-------------------

When dealing with long running executions, you may want to cancel some of them before they are done.

To cancel an execution, run:

.. sourcecode:: bash

    st2 execution cancel <existing execution id>


Inheriting all the environment variables which are accessible to the CLI and passing them to runner as env parameter
--------------------------------------------------------------------------------------------------------------------

Local, remote and Python runner support ``env`` parameter. This parameter tells
the runner which environment variables should be accessible to the action which
is being executed.

User can specify environment variables manually using ``env`` parameter exactly
the same way as other parameters.

For example:

.. sourcecode:: bash

    st2 run core.remote hosts=localhost env="key1=val1,key2=val2" cmd="echo ponies \${key1} \${key2}"

In addition to that, user can pass ``-e`` / ``--inherit-env`` flag to the
``action run`` command.

This flag will cause the command to inherit all the environment variables which
are accessible to the CLI and send them as an ``env`` parameter to the action.

Keep in mind that some global shell login variables such as ``PWD``, ``PATH``
and others are ignored and not inherited. Full list of ignored variables can
be found in `action.py file <https://github.com/StackStorm/st2/blob/master/st2client/st2client/commands/action.py>`_.

For example:

.. sourcecode:: bash

    st2 run --inherit-env core.remote cmd=...
