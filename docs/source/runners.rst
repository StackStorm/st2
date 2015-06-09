Action Runners
==============

An action runner is the execution environment for user-implemented
actions. For now |st2| comes with pre-canned action runners like a
remote runner and shell runner which provide for user-implemented
actions to be run remotely (via SSH) and locally. The objective is to
allow the Action author to concentrate only on the implementation of the
action itself rather than setting up the environment.

Local command runner (local-shell-cmd)
---------------------------------------

This is the local runner. This runner executes a Linux command on the same host
where |st2| components are running.

Runner parameters
~~~~~~~~~~~~~~~~~

* ``sudo`` (boolean) - The command will be executed with sudo.
* ``env`` (object) - Environment variables which will be available to the command(e.g. key1=val1,key2=val2)
* ``cmd`` (string) - Arbitrary Linux command to be executed on the host.
* ``kwarg_op`` (string) - Operator to use in front of keyword args i.e. "--" or "-".
* ``timeout`` (integer) - Action timeout in seconds. Action will get killed if it doesn't finish in timeout seconds.
* ``cwd`` (string) - Working directory where the command will be executed in

Local script runner (local-shell-script)
----------------------------------------

This is the local runner. Actions are implemented as scripts. They are executed
on the same hosts where |st2| components are running.

Runner parameters
~~~~~~~~~~~~~~~~~

* ``kwarg_op`` (string) - Operator to use in front of keyword args i.e. "--" or "-".
* ``timeout`` (integer) - Action timeout in seconds. Action will get killed if it doesn't finish in timeout seconds.
* ``sudo`` (boolean) - The command will be executed with sudo.
* ``cwd`` (string) - Working directory where the script will be executed in
* ``env`` (object) - Environment variables which will be available to the script(e.g. key1=val1,key2=val2)

Remote command runner (remote-shell-cmd)
----------------------------------------

This is a remote runner. This runner executes a Linux command on one or more
remote hosts provided by the user.

Runner parameters
~~~~~~~~~~~~~~~~~

* ``username`` (string) - Username used to log-in. If not provided, default username from config is used.
* ``private_key`` (string) - Private key used to log in. If not provided, private key from the config file is used.
* ``timeout`` (integer) - Action timeout in seconds. Action will get killed if it doesn't finish in timeout seconds.
* ``sudo`` (boolean) - The remote command will be executed with sudo.
* ``kwarg_op`` (string) - Operator to use in front of keyword args i.e. "--" or "-".
* ``password`` (string) - Password used to log in. If not provided, private key from the config file is used.
* ``parallel`` (boolean) - Default to parallel execution.
* ``cmd`` (string) - Arbitrary Linux command to be executed on the remote host(s).
* ``hosts`` (string) - A comma delimited string of a list of hosts where the remote command will be executed.
* ``env`` (object) - Environment variables which will be available to the command(e.g. key1=val1,key2=val2)
* ``cwd`` (string) - Working directory where the script will be executed in
* ``dir`` (string) - The working directory where the script will be copied to on the remote host.

Remote script runner (remote-shell-script)
------------------------------------------

This is a remote runner. Actions are implemented as scripts. They run on one or
more remote hosts provided by the user.

Runner parameters
~~~~~~~~~~~~~~~~~

* ``username`` (string) - Username used to log-in. If not provided, default username from config is used.
* ``private_key`` (string) - Private key used to log in. If not provided, private key from the config file is used.
* ``env`` (object) - Environment variables which will be available to the script(e.g. key1=val1,key2=val2)
* ``sudo`` (boolean) - The remote command will be executed with sudo.
* ``kwarg_op`` (string) - Operator to use in front of keyword args i.e. "--" or "-".
* ``password`` (string) - Password used to log in. If not provided, private key from the config file is used.
* ``parallel`` (boolean) - Default to parallel execution.
* ``hosts`` (string) - A comma delimited string of a list of hosts where the remote command will be executed.
* ``timeout`` (integer) - Action timeout in seconds. Action will get killed if it doesn't finish in timeout seconds.
* ``cwd`` (string) - Working directory where the script will be executed in.
* ``dir`` (string) - The working directory where the script will be copied to on the remote host.

Windows command runner (windows-cmd)
------------------------------------

Windows command runner allows you to run you to run command-line interpreter
(cmd) and PowerShell commands on Windows hosts.

For more information on enabling and setting up the Windows runner, please see
the following section - :doc:`./install/windows_runners`.

Runner parameters
~~~~~~~~~~~~~~~~~

* ``host`` (string) - Hostname or IP address of a host to execute the command on.
* ``username`` (string) - Username used to authenticate.
* ``password`` (string) - Password used to authenticate.
* ``cmd`` (object) - Command to run.
* ``timeout`` (integer) - Action timeout in seconds. Action will get killed if it doesn't finish in timeout seconds.

Windows script runner (windows-script)
--------------------------------------

Windows script runner allows you to run PowerShell scripts on Windows hosts.

For more information on enabling and setting up the Windows runner, please see
the following section - :doc:`./install/windows_runners`.

Runner parameters
~~~~~~~~~~~~~~~~~

* ``host`` (string) - Hostname or IP address of a host to execute the script on.
* ``username`` (string) - Username used to authenticate.
* ``password`` (string) - Password used to authenticate.
* ``share`` (object) - Name of the share where action script files are uploaded. Defaults to C$.
* ``timeout`` (integer) - Action timeout in seconds. Action will get killed if it doesn't finish in timeout seconds.

HTTP runner (http-request)
--------------------------

HTTP runner works by performing HTTP request to the provided URL.

Runner parameters
~~~~~~~~~~~~~~~~~

* ``cookies`` (object) - Optional cookies to send with the request.
* ``https_proxy`` (string) - A URL of a HTTPs proxy to use (e.g. http://10.10.1.10:3128).
* ``url`` (string) - URL to the HTTP endpoint.
* ``http_proxy`` (string) - A URL of a HTTP proxy to use (e.g. http://10.10.1.10:3128).
* ``headers`` (string) - HTTP headers for the request.
* ``allow_redirects`` (boolean) - Set to True if POST/PUT/DELETE redirect following is allowed.

Runner result
~~~~~~~~~~~~~

Result object from this runner contains the following keys:

* ``status_code`` (integer) - Response status code (e.g. 200, 404, etc.)
* ``body`` (string / object) - Response body. If the response body contains JSON
  and the response Content-Type header is ``application/json``, the body will be
  automatically parsed as JSON.
* ``parsed`` (boolean) - Flag which indicates if the response body has been parsed.
* ``headers`` - Response headers.

Python runner (python-script)
-----------------------------

This is a Python runner. Actions are implemented as Python classes with a
``run`` method. They run locally on the same machine where |st2| components are
running.

Runner parameters
~~~~~~~~~~~~~~~~~

* ``timeout`` (integer) - Action timeout in seconds. Action will get killed if it doesn't finish in timeout seconds.
* ``env`` (object) - Environment variables which will be available to the script(e.g. key1=val1,key2=val2)

Mistral runners (mistral-v2)
----------------------------

Those runners are built on top of the Mistral OpenStack project and support
executing complex work-flows. For more information, please refer to the
:doc:`Workflows </workflows>` and :doc:`Mistral </mistral>` section of documentation.

Runner parameters
~~~~~~~~~~~~~~~~~

* ``task`` (string) - The name of the task to run for reverse workflow.
* ``context`` (object) - Additional workflow inputs.
* ``workflow`` (string) - The name of the workflow to run if the entry_point is a workbook of many workflows. The name should be in the format "<pack_name>.<action_name>.<workflow_name>". If entry point is a workflow or a workbook with a single workflow, the runner will identify the workflow automatically.
