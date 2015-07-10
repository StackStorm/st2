.. NOTE: This file has been generated automatically, don't manually edit it

* ``sudo`` (boolean) - The command will be executed with sudo.
* ``env`` (object) - Environment variables which will be available to the command(e.g. key1=val1,key2=val2)
* ``cmd`` (string) - Arbitrary Linux command to be executed on the host.
* ``kwarg_op`` (string) - Operator to use in front of keyword args i.e. "--" or "-".
* ``timeout`` (integer) - Action timeout in seconds. Action will get killed if it doesn't finish in timeout seconds. 0 means no timeout.
* ``cwd`` (string) - Working directory where the command will be executed in