Running Self-Verification
'''''''''''''''''''''''

|st2| package-based installations come with a script, that allows to verify |st2| installation, using |st2| itself. 
Currently script covers the following aspects of |st2|:

* Basic ``st2`` commands (similar to the commands outlined in *Manual Verification* section)
* Examples pack installation
* Commands described in Quick Start
* Packs pack actions
* ActionChain and Mistral Workflows

To run the self-verification:

1. Switch to `root` user and save an authentication token into `ST2_AUTH_TOKEN` variable:

.. code-block:: bash

    sudo su
    export ST2_AUTH_TOKEN=`st2 auth testu -p testp -t`
    
2. Run ``st2-self-check`` script:

On Ubuntu / Debian:

.. code-block:: bash

    /usr/lib/python2.7/dist-packages/st2common/bin/st2-self-check
    
On RedHat / Fedora:

.. code-block:: bash

    /usr/lib/python2.7/site-packages/st2common/bin/st2-self-check


Manual Verification
'''''''''''''''''''

|st2| package-based installations have authentication enabled by default, therefore in the end of installation you will be provided with the default username and password. 
In order to use |st2|, including the commands below, you need to include a token, generated for the user, as a CLI argument or be provided as an environment variable.

.. include:: ../auth_usage.rst

Commands below assume that the token was provided as an environment variable.

Check that |st2| installation works OK: ::

    st2ctl status

    st2 --version
    st2 --help
    st2 action list
    st2 run core.local uname

Use the supervisor script to manage |st2| services: ::

    st2ctl start|stop|status|restart|restart-component|reload|clean

.. rubric:: What's Next?

* **Get going with** :doc:`/start`.

.. include:: /engage.rst

