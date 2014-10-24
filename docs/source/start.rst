Quick Start
=================

Got StackStorm :doc:`Installed </install/index>`? Enjoyed :doc:`the intro video <video>`? Let's go get your first automation going. But first, some terminology:

.. ref:: people 

* **Trigger** An external event that is mapped to a st2 input. It is the st2 invocation point. 
* **Sensor:** An adapter to convert an external event to a form st2 understands. This is usually a piece of python code.
* **Action:** An activity that user can run manually or use up in a rule as a response to the external event.
* **Rule:** A specification to invoke an "action" on a "trigger", selectively based on some criteria.
* **Workflow:** A chain of actions, with transitions and conditions, declaratively defined via workflow definition. Workflow *is* an action, and can be operated as such.

.. todo:: (dzimine) Refine terms. 


CLI Usage Examples
------------------

.. code-block:: bash

    st2 -h
    st2 action list
    st2 trigger list
    st2 rule list
    st2 run local -- uname -a
    st2 run remote host='host.1, host.2' user='myuser' -- ls -l

For details on using the CLI, please check the :doc:`/reference/cli` section.

Working with Actions
---------------------

Actions from action library can be invoked from st2 CLI, REST API, or
used in the rules. Lits the avaialbe actions: ::  

    st2 action list 

To introspect an action, do ``st2 action <actionname> get``, or,
``st2 run <actionname> --h ( --help)`` This shows action parameters so
that you know how to run it from CLI or use it in the rules. 

.. code-block:: bash

    st2 action get http
    st2 run http --help 

To run the action from cli, do ``st2 run <actionname> -- key=value positional arguments``. 
Some examples of using out-of-box actions:

.. code-block:: bash

    st2 run -j http url="http://localhost:9101/actions" method="GET"

    st2 run local -- uname -a

Use ``remote`` action to run linux command on multiple hosts over ssh. This assumes that passwordless SSH access is configured for the hosts, as described in :doc:`/install/ssh`.

.. code-block:: bash

    st2 run remote host='abc.example.com, cde.example.com' user='mysshuser' -- ls -l

**Note:** for ``local`` and ``remote`` actions, we use ``--`` to separate action
parameters to ensure that options keys, like ``-l`` or ``-a`` are
properly passed to the action. Alternatively, ``local`` and ``remote`` actions take 
the ``cmd`` parameter to pass crasily complex commands: ::

    st2 run remote hosts='localhost' cmd="for u in bob phill luke; do echo \"Logins by $u per day:\"; grep $u /var/log/secure | grep opened |awk '{print $1 \"-\" $2}' | uniq -c | sort; done;"

**How to get more actions?** Learn about installing and configuring integration packs in :doc:`/packs`. 
Convert your exisint scripts into st2 actions by adding metadata, or write custom actions: see :doc:`/actions` for details.

Defining Rules
--------------

A rule maps a trigger to an action: if THIS triggers, run THAT action.
It takes trigger parameters, sets matching criteria, and maps trigger
output parameters to action input parameters.

To see a list of available triggers: ``st2 trigger list``. The most
generic ones are timer triggers, webhook trigger ``st2.webhook``, and
``st2.generic.actiontrigger`` that is fired on each action completion.
For more interesting triggers, explore sensors under
`contrib/sandbox/ <../contrib/sandbox/>`__.

Rule is defined as JSON. The following is a sample rule definition
structure and a listing of the required and optional elements.

::

    {
            "name": "rule_name",                       # required
            "description": "Some test rule.",          # optional

            "trigger": {                               # required
                "name": "trigger_name"
            },

            "criteria": {                              # optional
                ...
            },

            "action": {                                # required
                "name": "action_name",
                "parameters": {                        # optional
                        ...
                }
            },

            "enabled": true                            # required
    }

The example at
`Stanley/contrib/examples/rules/sample-rule-with-webhook.json <../contrib/examples/rules/sample-rule-with-webhook.json>`__
takes a webhook and appends a payload to the file, but only if the name
matches:

::

    {
        "name": "st2.webhook-sample",
        "description": "Sample rule dumping webhook payload to a file.",

        "trigger": {
            "type": "st2.webhook",
            "parameters": {
                "url": "person"
            }
        },

        "criteria": {
            "trigger.name": {
                "pattern": "Joe",
                "type": "equals"
             }
        },

        "action": {
            "name": "local",
            "parameters": {
                "cmd": "echo \"{{trigger}}\" >> /tmp/st2.webhook-sample.out"
            }
        },

        "enabled": true
    }

To refer trigger payload in the action, use {{trigger}}. If trigger
payload is valid JSON, refer the parameters with
{{trigger.path.to.parameter}} in trigger.

Here is how to deploy the rule:

::

    # NOTE: The convention is to keep active rules in /opt/stackstorm/rules.
    cp contrib/examples/rules/sample-rule-with-webhook.json /opt/stackstorm/rules/

    st2 rule create /opt/stackstorm/rules/sample-rule-with-webhook.json
    st2 rule list
    st2 rule get st2.webhook-sample

Once the rule is created, the webhook begins to listen on
``http://{host}:6001/webhooks/generic/{url}``. Fire the post, check out
the file and see that it appends the payload if the name=Joe.

::

    curl http://localhost:6001/webhooks/generic/person -d '{"foo": "bar", "name": "Joe"}' -H 'Content-Type: application/json'
    tail /tmp/st2.webhook-sample.out

Criteria in the rule is expressed as:

::

    criteria: {
         "trigger.payload_parameter_name": {
            "pattern" : "value",
            "type": "matchregex"
          }
          ...
    }

Current criteria types are:
``'matchregex', 'eq' (or 'equals'), 'lt' (or 'lessthan'), 'gt' (or 'greaterthan'), 'td_lt' (or 'timediff_lt'), 'td_gt' (or 'timediff_gt')``.

**DEV NOTE:** The criterion are defined in
`st2common/st2common/operators.py <../st2common/st2common/operators.py>`__,
if you miss some code it up and submit a patch :)

See more rule examples at
`contrib/examples/rules/ <../contrib/examples/rules/>`__. The directory
`../contrib/sandbox/packages/ <../contrib/sandbox/packages/>`__ contains
some more rules.

Storing Reusable Parameters
---------------------------

The datastore service allow users to store common parameters and their
values as key value pairs within Stanley for reuse in sensors, actions,
and rules. It is handy to store some system or user variables (e.g.
configurations), refer them in a rule by ``{{system.my_parameter}}``, or
use in custom sensors and actions. Please refer to the
`datastore <datastore.md>`__ section for usage.

-------------------------------

Defining Custom Actions
-----------------------

See `actions.md <actions.md>`__ for more details on how to create custom
actions.

Defining Custom Triggers
------------------------

To introduce a custom trigger, you need to write a sensor - a code that
does the job of transferring the external event into Stanley trigger.
See `sensors.md <sensors.md>`__ for more details on how to write
sensors.

-------------------------------

.. rubric:: What's Next?

* Connect your monitoring - 
* Install and configure integration packs - 
* Configure SSH for `remote` action 
* Consume your existign scripts as st2 actions - 

.. include:: engage.rst
