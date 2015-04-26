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

