Purging old operational data from database
==========================================

If your StackStorm deployment is used for a sufficiently larger period of time or you have
a lot of executions happening/triggers coming in, database fills up. If you are
looking for a way to purge old data in bulk for performance reasons or cleaning up the db,
the following tools will help you do so.

Purging executions older than some timestamp
--------------------------------------------

::

    st2-purge-executions.py --timestamp="2015-11-25T21:45:00.000000Z"

The timestamp provided is interpreted as UTC timestamp. Please perform all necessary timezone
conversions and specify UTC timestamp.

You can also delete executions for a particular ``action_ref`` by specifying an action_ref parameter
to the tool.

::

    st2-purge-executions.py --timestamp="2015-11-25T21:45:00.000000Z" --action-ref="core.localzz"

By default, only executions in completed state viz ``succeeded``, ``failed``, ``canceled``
and ``timed_out`` are deleted. If you want to purge all models irrespective of status,
you can pass the --purge-incomplete option to the script.

::

    st2-purge-executions.py --timestamp="2015-11-25T21:45:00.000000Z" --purge-incomplete

Depending on how much data there is, the tool might be running longer. Therefore, please run it
inside a screen/tmux session. For example,

::

    screen -d -m -S purge-execs st2-purge-executions.py --timestamp="2015-11-25T21:45:00.000000Z"

Purging trigger instances older than some timestamp
---------------------------------------------------

::

    st2-purge-trigger-instances.py --timestamp="2015-11-25T21:45:00.000000Z"

Again, the timestamp provided is interpreted as UTC timestamp. Please perform all necessary timezone
conversions and specify UTC timestamp.

Depending on how much data there is, the tool might be running longer. Therefore, please run it
inside a screen/tmux session. For example,

::

    screen -d -m -S purge-instances st2-purge-trigger-instances.py --timestamp="2015-11-25T21:45:00.000000Z"
