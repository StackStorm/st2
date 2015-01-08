Rules
=====

|st2| uses rules and worfklows to capture operational patterns as automations.
Rules map triggers to actions (or workflows), apply matching criteria and
map trigger payload to action inputs.

Rule spec is defined in YAML. JSON is supported for backward compatibility.
The following is a sample rule definition structure and a listing of the
required and optional elements.

.. code-block:: yaml

    ---
        name: "rule_name"                      # required
        description: "Rule description."       # optional
        enabled: true                          # required

        trigger:                               # required
            type: "trigger_type_ref"

        criteria:                              # optional
            # See below ...

        action:                                # required
            ref: "action_ref"
            parameters:                        # optional
                foo: "bar"
                baz: 1


Criteria in the rule is expressed as:

.. code-block:: yaml

    criteria:
        trigger.payload_parameter_name1:
            type: "matchregex"
            pattern : "^value$"
        trigger.payload_parameter_name2:
            type: "iequals"
            pattern : "watchevent"
        # more variables

``type`` specifies which criteria comparison operator to use and ``pattern`` specifies the pattern
which gets passed to the operator function.

In the ``matchregex`` case, ``pattern`` is a regular expression pattern which the trigger value
needs to match.

A list of all the available criteria operators is described bellow. If you are missing some
operator, you are welcome to code it up and submit a patch :)

If the criteria key contains an operator like (-) then use the dictionary lookup format for specifying
the criteria key. In case of a webhook based rule it is typical for the header of the posted event to
contain such values e.g.

.. code-block:: yaml

    criteria:
        trigger.headers['X-Custom-Header']:
            type: "eq"
            pattern : "customvalue"


To deploy a rule, use CLI:

.. code-block:: bash

    st2 rule create /opt/stackstorm/packs/examples/rules/sample_rule_with_webhook.yaml
    st2 rule create /opt/stackstorm/examples/rules/sample_rule_with_webhook.yaml
    st2 rule list
    st2 rule get examples.webhook_file

By default, |st2| doesn't load the rules deployed under ``/opt/stackstorm/packs/${pack_name}/rules/``. However you can force
load them with ``st2 run packs.load register=rules``

Supported criteria comparision operators
----------------------------------------

This section describes all the available operators which can be used in the criteria.

.. note::

    **For Developers:** The criteria comparision functions are defined in
    :github_st2:`st2/st2common/st2common/operators.py </st2common/st2common/operators.py>`.

* ``matchregex`` - Regular expression match.
* ``equals`` - Equality comparison.
* ``iequals`` - Case insensitive equality comparison (trigger value needs to be string).
* ``contains`` - String contains comparison.
* ``icontains`` - Case insensitive string contains comparison.
* ``ncontains`` - String doesn't contain comparison.
* ``startswith`` - String startswith comparison.
* ``istartswith`` - Case insensitive string startswith comparison.
* ``endswith`` - String endswith comparison.
* ``iendswith`` - Case insensitive string endswith comparison.
* ``incontains`` - Case insensitive string doesn't contain comparison.
* ``lessthan`` - Less than comparison.
* ``greaterthan`` - Greater than comparison.
* ``timediff_lt`` - Timestamp lower than comparison.
* ``timediff_gt`` - Timestamp greater than comparison.

matchregex
~~~~~~~~~~

Checks that trigger value matches the provided regular expression.

equals
~~~~~~

Checks that the trigger value exactly matches the provided pattern.

iequals
~~~~~~~

Checks that the trigger value matches the provided pattern ignoring the casing.

contains
~~~~~~~~

Checks that the trigger value contains the provided pattern.

icontains
~~~~~~~~~

Checks that the trigger value contains the provided pattern ignoring the casing.

ncontains
~~~~~~~~~

Checks that the trigger value doesn't contains the provided pattern.

incontains
~~~~~~~~~~

Checks that the trigger value doesn't contains the provided pattern ignoring the casing.

lessthan
~~~~~~~~

Checks that the trigger value is less than the provided pattern.

greaterthan
~~~~~~~~~~~

Checks that the trigger value is greater than the provided pattern.

timediff_lt
~~~~~~~~~~~

Checks that the time difference between the trigger value is less than the provided pattern.

timediff_gt
~~~~~~~~~~~

Checks that the time difference between the trigger value is greater than the provided pattern.

Rule location
-------------

Custom rules can be placed in ``/opt/stackstorm/packs/default/rules`` and registered using ``st2 rule create ${PATH_TO_RULE}``. Placing the rule files in alternate locations is acceptable. Note that the ``st2 rule create`` command will read rule from the filesystem local to itself.

.. rubric:: What's Next?

* See :doc:`/start` for a simple example of creating and deploying a rule.
* Explore automations on `st2contrib`_ community repo.
* Learn more about :doc:`sensors`.

Testing Rules
-------------

To make testing the rules easier we provide a tool which allows you to evaluate rules against
trigger instances without running any of the StackStorm components.

The tool works by taking a path to the file which contains rule definition and a file which
contains trigger instance definition.

Both files need to contain definitions in YAML or JSON format. For the rule, you can use the same
file you would use to create the rule using the command line tool (the file you
pass to ``st2 rule create``)

And for the trigger instance, the definition file needs contain the following keys:

* ``trigger`` - Full reference to the trigger (e.g. ``core.st2.IntervalTimer``,
  ``slack.message``, ``irc.pubmsg``, ``twitter.matched_tweet``, etc.).
* ``payload`` - Trigger payload. The payload itself is specific to the trigger in question. To
  figure out the trigger structure you can look at the pack README or look for the
  ``trigger_types`` section in the sensor metadata file which is located in the ``packs/<pack
  name>/sensors/`` directory.

If the trigger instance matches, ``=== RULE MATCHES ===`` will be printed and the tool will exit
with ``0`` status code. On the other hand, if the rule doesn't match,
``=== RULE DOES NOT MATCH ===`` will be printed and the tool will exit with ``1`` status code.

Here are some examples on how to use the tool.

my_rule.yaml:

.. code-block:: yaml

    ---
      name: "relayed_matched_irc_message"
      description: "Relay IRC message to Slack if the message contains word StackStorm"
      enabled: true

      trigger:
        type: "irc.pubmsg"
        parameters: {}

      criteria:
          trigger.message:
              type: "icontains"
              pattern: "StackStorm"

      action:
        ref: "slack.post_message"
        parameters:
            message: "{{trigger.source.nick}} on {{trigger.channel}}: {{trigger.message}}"
            channel: "#irc-relay"

trigger_instance_1.yaml:

.. code-block:: yaml

    ---
        trigger: "irc.pubmsg"
        payload:
          source:
              nick: "Kami_"
              host: "gateway/web/irccloud.com/x-uvv"
          channel: "#stackstorm"
          timestamp: 1419166748,
          message: "stackstorm is cool!"

trigger_instance_2.yaml:

.. code-block:: yaml

    ---
        trigger: "irc.pubmsg"
        payload:
          source:
              nick: "Kami_"
              host: "gateway/web/irccloud.com/x-uvv"
          channel: "#stackstorm"
          timestamp: 1419166748,
          message: "blah blah"

.. code-block:: bash

    rule_tester --rule=./my_rule.yaml --trigger-instance=./trigger_instance_1.yaml
    echo $?

Output:

.. code-block:: bash

    === RULE MATCHES ===
    0

.. code-block:: bash

    rule_tester --rule=./my_rule.yaml --trigger-instance=./trigger_instance_2.yaml
    echo $?

Output:

.. code-block:: bash

    === RULE DOES NOT MATCH ===
    1

.. include:: engage.rst
