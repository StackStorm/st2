Purging old operational data from database
==========================================

If your |st2| deployment is used for a sufficiently larger period of time or
you have a lot of executions happening/triggers coming in, database fills up.
If you are looking for a way to purge old data in bulk for performance reasons
or cleaning up the db, you have two options described below.

1. Automatic purging via garbage collector service
--------------------------------------------------

|st2| ships with a special service which is designed to periodically collect
garbage and old data (old action execution, live action and trigger instance
database objects).

The actual collection threshold is very user specific (it depends on your
requirements, policies, etc.) so garbage collection of old data is disabled
by default.

If you want to enable it, you need to configure TTL (in days) for action
executions and trigger instances in ``st2.conf`` as shown below:

.. sourcecode:: ini

    [garbagecollector]
    logging = st2reactor/conf/logging.garbagecollector.conf

    action_executions_ttl = 30
    trigger_instances_ttl = 30

In this case action executions and trigger instances older than 30 days will be
automatically deleted.

Keep in mind that the lowest supported TTL right now is 7 days. If you want to
delete old data more often then that, you should look at the purge scripts
described below.

2. Manual purging using purge scripts
-------------------------------------

If for some reason you don't want to use automatic purging via garbage collector
service you can perform purging manually using the scripts described below.

Purging executions older than some timestamp
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    st2-purge-executions --timestamp="2015-11-25T21:45:00.000000Z"

The timestamp provided is interpreted as UTC timestamp. Please perform all necessary timezone
conversions and specify UTC timestamp.

You can also delete executions for a particular ``action_ref`` by specifying an action_ref parameter
to the tool.

::

    st2-purge-executions --timestamp="2015-11-25T21:45:00.000000Z" --action-ref="core.localzz"

By default, only executions in completed state viz ``succeeded``, ``failed``, ``canceled``, ``timeout``
and ``abandoned`` are deleted. If you want to purge all models irrespective of status,
you can pass the --purge-incomplete option to the script.

::

    st2-purge-executions --timestamp="2015-11-25T21:45:00.000000Z" --purge-incomplete

Depending on how much data there is, the tool might be running longer. Therefore, please run it
inside a screen/tmux session. For example,

::

    screen -d -m -S purge-execs st2-purge-executions --timestamp="2015-11-25T21:45:00.000000Z"

Purging trigger instances older than some timestamp
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    st2-purge-trigger-instances --timestamp="2015-11-25T21:45:00.000000Z"

Again, the timestamp provided is interpreted as UTC timestamp. Please perform all necessary timezone
conversions and specify UTC timestamp.

Depending on how much data there is, the tool might be running longer. Therefore, please run it
inside a screen/tmux session. For example,

::

    screen -d -m -S purge-instances st2-purge-trigger-instances --timestamp="2015-11-25T21:45:00.000000Z"
