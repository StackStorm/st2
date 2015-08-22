Action Runners
==============

An action runner is the execution environment for user-implemented
actions. For now |st2| comes with pre-canned action runners like a
remote runner and shell runner which provide for user-implemented
actions to be run remotely (via SSH) and locally. The objective is to
allow the Action author to concentrate only on the implementation of the
action itself rather than setting up the environment.

Exit Codes
----------
Normally an exit code of a runner is defined by an exit code of a script or a command they execute. All runners return timeout exit code (-9) in case when a command or a script did not complete its execution within specified timeout.

Local command runner (local-shell-cmd)
---------------------------------------

This is the local runner. This runner executes a Linux command on the same host
where |st2| components are running.

Runner parameters
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/local_shell_cmd.rst

Local script runner (local-shell-script)
----------------------------------------

This is the local runner. Actions are implemented as scripts. They are executed
on the same hosts where |st2| components are running.

Runner parameters
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/local_shell_script.rst

Remote command runner (remote-shell-cmd)
----------------------------------------

This is a remote runner. This runner executes a Linux command on one or more
remote hosts provided by the user.

Runner parameters
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/remote_shell_cmd.rst

Remote script runner (remote-shell-script)
------------------------------------------

This is a remote runner. Actions are implemented as scripts. They run on one or
more remote hosts provided by the user.

Runner parameters
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/remote_shell_script.rst

.. note::

    Until v0.13 remote script runner and remote command runner used Fabric to remote to boxes.
    In 0.13 Fabric is replaced with Paramiko with eventlets.
    If for some reason you need to use old Fabric based
    implementation instead, set ``use_paramiko_ssh_runner = False`` in ``[ssh_runner]`` section in ``/etc/st2/st2.conf``.

Windows command runner (windows-cmd)
------------------------------------

Windows command runner allows you to run you to run command-line interpreter
(cmd) and PowerShell commands on Windows hosts.

For more information on enabling and setting up the Windows runner, please see
the following section - :doc:`./install/windows_runners`.

Runner parameters
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/windows_cmd.rst

Windows script runner (windows-script)
--------------------------------------

Windows script runner allows you to run PowerShell scripts on Windows hosts.

For more information on enabling and setting up the Windows runner, please see
the following section - :doc:`./install/windows_runners`.

Runner parameters
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/windows_script.rst

HTTP runner (http-request)
--------------------------

HTTP runner works by performing HTTP request to the provided URL.

Runner parameters
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/http_request.rst

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
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/python_script.rst

Mistral runner (mistral-v2)
---------------------------

Those runners are built on top of the Mistral OpenStack project and support
executing complex work-flows. For more information, please refer to the
:doc:`Workflows </workflows>` and :doc:`Mistral </mistral>` section of documentation.

Runner parameters
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/mistral_v2.rst

CloudSlang runner (cloudslang)
------------------------------

This runner is built on top of the CloudSlang project and supports
executing complex workflows. For more information, please refer to the
:doc:`Workflows </workflows>` and :doc:`CloudSlang </cloudslang>` section of documentation.

Note: This runner is currently in an experimental phase which means that there
might be bugs and the external user facing API might change.

Runner parameters
^^^^^^^^^^^^^^^^^

.. include:: _includes/runner_parameters/cloudslang.rst

