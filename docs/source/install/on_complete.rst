Check that |st2| installation works OK: ::

    st2ctl status

    st2 --version
    st2 --help

    # If AUTH enabled: authenticate and export the token env variable
    # so you don't need to pass it as parameter on every command.
    st2 auth testu -p testp
    export ST2_AUTH_TOKEN=`st2 auth -t -p testp testu`

    st2 action list
    st2 run core.local uname

Use the supervisor script to manage |st2| services: ::

    st2ctl start|stop|status|restart|restart-component|reload|clean

.. rubric:: What's Next?

* Get going with :doc:`/start`.
* How to configure and use :doc:`authentication <../config/authentication>`.
* Check out `tutorials on stackstorm.com <http://stackstorm.com/category/tutorials/>`__ - a growing set of practical examples of automating with StackStorm.

.. include:: /engage.rst

