Quick Start
=================

Now that you have StackStorm :doc:`installed </install/index>`, and hopefully
enjoyed :doc:`the intro video <video>`, let's build a first automation.
This guide will walk you through StackStorm basics and help you build and run
an automation: a rule that triggers an action on external event.


Explore StackStorm with CLI
----------------------------
The best way to explore StackStorm is to use CLI. Start by firing few commands:

.. code-block:: bash

    st2 --version 
    # Get help. It's a lot. Explore.
    st2 -h
    # List the actions from a 'core' pack
    st2 action list --pack=core
    st2 trigger list
    st2 rule list
    # Run a local shell command 
    st2 run core.local -- uname -a
    # See the execution results
    st2 execution list 
    # Fire a shell comand on remote hosts. Requires passwordless SSH configured.
    st2 run core.remote host='host.1, host.2' user='myuser' -- ls -l

The default “all-in-one” installation deploys CLI along with the StackStorm
services. CLI can be used to access StackStorm service remotely. All StackStorm
operations are also available via REST API and Python bindings.
Check the :doc:`CLI and Python Client </reference/cli>` reference for details.

Work with Actions
---------------------

Out of the box, StackStorm’s Action library contains few generic actions.
It can be easily extended by getting actions from the community or consuming
your existing scripts - `more on that later`. Browse Action Library with 
``st2 action list``. Action is called by `ref` as ``pack.action_name``
(e.g. ``core.local``). Learn more about an aciont by doing
``st2 action <action> get``, or, ``st2 run <action> --h ( --help)``: it shows
description along with action parameters so that you know how to run it 
from CLI or use it in rules and workflows. 


.. code-block:: bash

    # List all the actions in the library
    st2 action list 
    # Get action metadata
    st2 action get core.http
    # Display action details and parameters.
    st2 run core.http --help 

To run the action from cli, do
``st2 run <action> -- key=value positional arguments``. 

.. code-block:: bash

    # Run a local command 
    st2 run core.local -- uname -a

    # HTTP REST call to st2 action endpoint
    st2 run -j core.http url="http://localhost:9101/actions" method="GET"

Use ``remote`` action to run linux command on multiple hosts over ssh. 
This assumes that passwordless SSH access is configured for the hosts,
as described in `Configure SSH </install/config.rst#configure-ssh>`__ section.

.. code-block:: bash

    st2 run core.remote host='abc.example.com, cde.example.com' user='mysshuser' -- ls -l

**Note:** for ``local`` and ``remote`` actions, we use ``--`` to separate action
parameters to ensure that options keys, like ``-l`` or ``-a`` are
properly passed to the action. Alternatively, ``local`` and ``remote`` actions take 
the ``cmd`` parameter to pass crasily complex commands: ::

    st2 run core.remote hosts='localhost' cmd="for u in bob phill luke; do echo \"Logins by $u per day:\"; grep $u /var/log/secure | grep opened |awk '{print $1 \"-\" $2}' | uniq -c | sort; done;"

Check the action execution history and details of action executions with ``st2 execution`` command:

.. code-block:: bash 

    st2 execution list
    st2 execution get <execution_id>

That's it. You have learned to use StackStorm's action library. Let's proceed to automations.


Define and deploy a Rule
-------------------------

StackStorm uses rules to fire actions or workflows when events happen.
Events are typically monitored by sensors. When sensor catches an event,
it fires a trigger. Trigger trips the rule, the rule checks the criteria
and if it matches, it runs an action. Easy enough. Let’s look at an example.

Sample rule: :github_st2:`sample-rule-with-webhook.json 
</contrib/examples/rules/sample-rule-with-webhook.json>` : 

.. literalinclude:: /../../contrib/examples/rules/sample_rule_with_webhook.json
    :language: json


The rule definition is a JSON spec with thee sections: trigger, criteria, and action.
It configures the wehbook trigger with url, applies filtering criteria based trigger
parameters. This one configures a webhook wiht ``sample`` sub-url so it listens
on ``http://{host}:6001/webhooks/generic/sample``.
When it fires, it appends a payload to the file, only if the ``name``
value in payload is ``st2``. See :doc:`rules` for detailed rule anatomy. 

What are the other availabe triggers to use in rules? Just like with ations,
use CLI to browse triggers, learn what the trigger does, 
how to configure it, and what is it’s payload structure: 

.. code-block:: bash

    # List all available triggers
    st2 trigger list

    # Check details on Interval Timer trigger
    st2 trigger get core.st2.IntervalTimer

    # Check details on the Webhook trigger 
    st2 trigger get core.st2.webhook

Jinga syntax is used to refer variables in criteria or in action. Trigger
payload is referred with ``{{trigger}}``. If trigger payload is valid JSON,
it is parsed and can be accessed like ``{{trigger.path.to.parameter}}``.

While the most data are retrieved as needed by StackStorm, you may need to
store and share some common variables. Use st2 datastore service to store
the values and reference them in rules and workflows
as ``{{system.my_parameter}}``. 


.. code-block:: bash
    st2 key create name=user value=stanley
    st2 key list

The rule is ready. StackStorm can be configured to auto-load the rules,
or they are deployed with API or CLI: 

.. code-block:: bash
    
    st2 rule create /opt/stackstorm/examples/rules/sample_rule_with_webhook.json
    st2 rule list
    st2 rule get examples.webhook_file

Once the rule is created, the webhook begins to listen on
``http://{host}:6001/webhooks/generic/{url}``. Fire the post, check out
the file and see that it appends the payload if the name=Joe.

.. code-block:: bash

    # Post to the webhook
    curl http://localhost:6001/webhooks/generic/sample -d '{"foo": "bar", "name": "st2"}' -H 'Content-Type: application/json'
    # Check if the action got executed 
    st2 execution list
    # Check that the rule worked
    tail /tmp/st2.webhook_sample.out

Congratulations, your first StackStorm rule is up and running!

Basic examples of rules, along with sample actions and sensors can be
found at ``/usr/share/doc/st2/examples/``. To get them deployed, copy them
to /opt/stackstorm/ and reload the content by running ``st2 run packs.load``.
For more content examples checkout `st2contrib`_ community repo on GitHub. 


Basic Trobuleshooting
----------------------
If something goes wrong: 

* Check recent executions: ``st2 execution list``
* Check the logs at ``/var/log/st2.`` 
* Use service control st2ctl to check service status, reboot the system, or clean the db.
* Engage with developers


-------------------------------

.. rubric:: What's Next?

* Get more actions, triggers, rules:

    * Install and configure integration packs from `st2contrib`_  - :doc:`/packs`
    * Convert your exisint scripts into st2 actions by adding metadata, or write custom actions: see :doc:`/actions` for details.
* Connect with your monitoring system: - :doc:`resources/monitoring`
* Configure SSH for `remote` actions  - :ref:`configure-ssh`
* Use worklows to stitch actions into higher level automations - :doc:`/workflows`.


.. include:: engage.rst

