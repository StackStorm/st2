Rules
======================================

StackStorm uses rule and worfklows to capture operational patterns as automations. 
Rules map triggers to actions (or workflows), applying matching criterias and 
mapping trigger payload to action inputs.

Rule spec is defined as JSON. The following is a sample rule definition
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

Criteria in the rule is expressed as:

::

    criteria: {
         "trigger.payload_parameter_name": {
            "pattern" : "value",
            "type": "matchregex"
          }
          ...
    }

Current criteria types are: ``matchregex``, ``eq`` (or ``equals``), ``lt`` (or ``lessthan``), ``gt`` (or ``greaterthan``), ``td_lt`` (or ``timediff_lt``), ``td_gt`` (or ``timediff_gt``).  **For Developers:** The criterion are defined in :github_st2:`st2/st2common/st2common/operators.py </st2common/st2common/operators.py>`,
if you miss some criteria - welcome to code it up and submit a patch :)

.. todo:: How to operate the rules. 

To deploy a rule, use CLI:

.. code-block:: bash
    
    st2 rule create /opt/stackstorm/examples/rules/sample_rule_with_webhook.json
    st2 rule list
    st2 rule get examples.webhook_file

By default, StackStorm doesn't load the rules deployed under ``/opt/stackstorm/``. However you can force it 
load them with ``st2 run pacsk.load register=rules``
place them in 
-------------------------------

.. rubric:: What's Next?

* See :doc:`/start` for a simple example of creating and deploying a rule. 
* Explore automations on `st2contrib`_ comminity repo.
* Learn more about :doc:`sensors`. 

.. include:: engage.rst
