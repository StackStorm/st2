Writing Custom Actions
======================

Action scripts are user supplied content written in arbitrary programming
language to operate against external system. Depending on the runner type,
those scripts are either executed on a remote host or on a local system where
Stanley action runner is running.

This section describes how to extend Stanley functionality by writing custom
actions. It also includes information such as best practices and other things
to keep in mind when writing custom actions.

Action Metadata
---------------

Action metadata file is used to describe the action. It includes information
such as action entry point, action parameter descriptions, and more. It's
stored in a JSON format in a file named ``<action_name>.json``.

For example, if the action script file name is ``twilio_send_sms.py``, then the
meta data is stored in a file named ``twilio_send_sms.json``.

Runner Specific Documentation
-----------------------------

:doc:`Writing custom Python actions <python_actions>`
