History and Audit
=================

These are records maintained by StackStorm of past action executions.  These records include information about what events triggered what rules and then what actions; common uses for this information includes root cause analysis reporting as well as operational control as well as collaboration.

This information is stored in two forms

* Database (accessible via CLI)
* Audit log (/var/log/st2/st2*.audit.log)

There are a couple of options to access history and audit records.

CLI
---

All execution records are accessible by the ``st2 execution *`` command family.

.. code-block:: bash

    # to see last 5 executions
    $ st2 execution list -n 5
    +--------------------------+---------------+--------------+-----------+-----------------------------+
    | id                       | action        | context.user | status    | start_timestamp             |
    +--------------------------+---------------+--------------+-----------+-----------------------------+
    | 5452ed4e0640fd6b59e75908 | core.http     | stanley      | succeeded | 2014-10-31T02:00:46.679000Z |
    | 5452ed480640fd6b59e75907 | core.local    | stanley      | succeeded | 2014-10-31T02:00:40.851000Z |
    | 5452ed440640fd6b59e75906 | core.remote   | stanley      | succeeded | 2014-10-31T02:00:36.718000Z |
    | 5452ed3f0640fd6b59e75905 | aws.vm.create | stanley      | succeeded | 2014-10-31T02:00:31.383000Z |
    | 5452ed3d0640fd6b59e75904 | core.sendmail | stanley      | succeeded | 2014-10-31T02:00:29.356000Z |
    +--------------------------+---------------+--------------+-----------+-----------------------------+

    # To see the output of a specific execution. The -j switch prints out the result in json.
    $ st2 execution get 5452ed4e0640fd6b59e75908 -j
    {
        "status": "succeeded",
        "start_timestamp": "2014-10-31T02:00:46.679000Z",
        "parameters": {
            "cmd": "ifconfig"
        },
        "callback": {},
        "result": {
            ...
        },
        "context": {
            "user": "stanley"
        },
        "action": "core.local",
        "id": "5452ed4e0640fd6b59e75908"
    }

Use ``st2 execution list -h`` and ``st2 execution get -h`` to explore options available with each of these commands.

Owing to the fact that execution history can contain many records a command like ``st2 execution list --action ${action_reference} -n 10`` is particularly useful, it provides the last 10 execution of a specified action.


Logstash
--------

The audit logs are a lot more comprehensive in the information they contain. It is useful to view these in a tool like LogStash which provides excellent search, sort and aggregation features.

Check out LogStash configuration and Kibana dashboard for pretty logging and audit at :github_contrib:`st2contrib/extra/logstash </extra/logstash>`


Coming soon
-----------

We are working on analytics for system operations, which may include analysis based upon underlying logs as well as enhancements to our GUI for this purpose.
