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

    st2 run core.remote hosts=localhost env="key1=val1,key2=val2" cmd="echo ponies \${key1} \${key2}

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
