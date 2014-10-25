Quick Start
=================

Got StackStorm :doc:`Installed </install/index>`? Enjoyed :doc:`the intro video <video>`? Let's go get your first automation going. But first, some terminology:

* **Trigger** An external event that is mapped to a st2 input. It is the st2 invocation point. 
* **Sensor:** An adapter to convert an external event to a form st2 understands. This is usually a piece of python code.
* **Action:** An activity that user can run manually or use up in a rule as a response to the external event.
* **Rule:** A specification to invoke an "action" on a "trigger", selectively based on some criteria.
* **Workflow:** A chain of actions, with transitions and conditions, declaratively defined via workflow definition. Workflow *is* an action, and can be operated as such.

.. todo:: (dzimine) Refine terms. 


CLI Usage Examples
------------------

.. code-block:: bash

    st2 --version 
    st2 -h
    st2 action list
    st2 trigger list
    st2 rule list
    st2 run core.local -- uname -a
    st2 execution list 
    st2 run core.remote host='host.1, host.2' user='myuser' -- ls -l

For details on using the CLI, please check the :doc:`/reference/cli` section.

Working with Actions
---------------------

Actions from action library can be invoked from st2 CLI, REST API, or
used in the rules. Lits the avaialbe actions: ::  

    st2 action list 

To introspect an action, do ``st2 action <action> get``, or,
``st2 run <action> --h ( --help)`` This shows action parameters so
that you know how to run it from CLI or use it in the rules. Action is referenced as ``pack.action_name`` (e.g. ``core.local``)

.. code-block:: bash

    st2 action get core.http
    st2 run core.http --help 

To run the action from cli, do ``st2 run <action> -- key=value positional arguments``. 
Some examples of using out-of-box actions:

.. code-block:: bash

    # Run a local command 
    st2 run core.local -- uname -a

    # HTTP REST call to st2 action endpoint
    st2 run -j core.http url="http://localhost:9101/actions" method="GET"

Use ``remote`` action to run linux command on multiple hosts over ssh. This assumes that passwordless SSH access is configured for the hosts, as described in :doc:`/install/ssh`.

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

**How to get more actions?** Learn about installing and configuring integration packs in :doc:`/packs`. 
Convert your exisint scripts into st2 actions by adding metadata, or write custom actions: see :doc:`/actions` for details.

Defining Rules
--------------

A rule maps a trigger to an action: if THIS triggers, run THAT action.
It takes trigger parameters, sets matching criteria, and maps trigger
output parameters to action input parameters.

To see a list of available triggers: ``st2 trigger list``. The most
generic ones are timer triggers, webhook trigger ``core.st2.webhook``, and
``core.st2.generic.actiontrigger`` that is fired on each action completion.
Use ``st2 trigger get <trigger>`` to introspect trigger input parameters and payload structure: 

.. code-block:: bash
    
    st2 trigger list
    st2 trigger get core.st2.IntervalTimer
    st2 trigger get core.st2.webhook


Rule is defined as JSON. The following is a sample rule definition
structure and a listing of the required and optional elements.

.. code-block:: json

    {
            "name": "rule_name",                       # required
            "description": "Rule description",         # optional

            "trigger": {                               # required
                "name": "trigger_name"
            },

            "criteria": {                              # optional
                ...
            },

            "action": {                                # required
                "ref": "action_name",
                "parameters": {                        # optional
                        ...
                }
            },

            "enabled": true                            # required
    }

Let's take a simple example. The rule defined in `sample-rule-with-webhook.json` 
takes a webhook and appends a payload to the file, but only if the ``name``
field matches:

.. literalinclude:: /../../contrib/examples/rules/sample-rule-with-webhook.json
    :language: json

To refer trigger payload in criteria or in action, use ``{{trigger}}``. If trigger
payload is valid JSON, refer the parameters with
``{{trigger.path.to.parameter}}`` in trigger. Trigger input and output parameters can be introspected by calling ``st2 trigger get <trigger>``. 

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

Criteria in the rule is expressed as:

::

    criteria: {
         "trigger.payload_parameter_name": {
            "pattern" : "value",
            "type": "matchregex"
          }
          ...
    }

Current criteria types are: ``matchregex``, ``eq`` (or ``equals``), ``lt`` (or ``lessthan``), ``gt`` (or ``greaterthan``), ``td_lt`` (or ``timediff_lt``), ``td_gt`` (or ``timediff_gt``). **DEV NOTE:** The criterion are defined in
`st2common/st2common/operators.py <../st2common/st2common/operators.py>`__,
if you miss some criteria - welcome to code it up and submit a patch :)

Basic examples of rules, along with sample actions and sensors are deployed to ``/opt/stacstorm/examples``. 
For more content examples checkout `st2contrib <http://www.github.com/stackstorm/st2contrib>`__ community repo on GitHub. 

Storing Reusable Parameters
---------------------------

The datastore service allow users to store common parameters and their
values as key value pairs within Stanley for reuse in sensors, actions,
and rules. It is handy to store some system or user variables (e.g.
configurations), refer them in a rule by ``{{system.my_parameter}}``, or
use in custom sensors and actions. Please refer to the
`datastore <datastore.md>`__ section for usage.

:: 

    st2 key create name=user value=stanley
    st2 key list


Basic Trobuleshooting
----------------------

* Logs are in ``/opt/var/st2``. st2api 
* Service contril script is ``st2ctl`` - status, bounce off the system...
* List recent executions ``st2 execution list``
* Talk to developers :)

.. todo:: Refnie basic troubleshooting

-------------------------------

.. rubric:: What's Next?

* Connect your monitoring - TBD, article
* Install and configure integration packs - :doc:`/packs`
* Configure SSH for `remote` action  - :doc:`/install/ssh`
* Consume your existign scripts as st2 actions - 
* Learn how to write custom sensors and actions - 

.. include:: engage.rst
