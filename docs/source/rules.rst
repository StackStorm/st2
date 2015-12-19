Rules
=====

|st2| uses rules and worfklows to capture operational patterns as automations.
Rules map triggers to actions (or workflows), apply matching criteria and
map trigger payload to action inputs.

Rule Structure
--------------

Rules are defined in YAML; JSON is supported for backward compatibility. Rule definition structure, as well as required and optional elements are listed below:

.. code-block:: yaml

    ---
        name: "rule_name"                      # required
        pack: "examples"                       # optional
        description: "Rule description."       # optional
        enabled: true                          # required

        trigger:                               # required
            type: "trigger_type_ref"

        criteria:                              # optional
            trigger.payload_parameter_name1:
                type: "matchregex"
                pattern : "^value$"
            trigger.payload_parameter_name2:
                type: "iequals"
                pattern : "watchevent"

        action:                                # required
            ref: "action_ref"
            parameters:                        # optional
                foo: "bar"
                baz: "{{trigger.payload_parameter_1}}"

The generic form of a rule is:

* The ``name`` of the rule.
* The ``pack`` that the rule belongs to. `default` is assumed if a pack is not specified.
* The ``description`` of the rule
* The ``enabled`` state of a rule (``true`` or ``false``)
* The type of ``trigger`` emitted from sensors to monitor, which may consist of:
  * parameters associated with a sensor/trigger
* An optional set of **criteria**, consisting of:
  * An attribute of the trigger payload
  * The ``type`` of criteria comparision
  * The ``pattern`` to match against
* The ``action`` to execute when a rule is matched, consisting of:
  * The ``ref`` (action/workflow) to execute
  * An optional set of ``parameters`` to pass to the action execution.


Trigger
-------

The trigger in a rule specifies which incoming events should be inspected for potential match against this rule.
It is possible to view all the triggers configured on a system via the command line with the ``st2 trigger list``
command

.. code-block:: shell

    vagrant@st2express:~$ st2 trigger list
    +--------------------------------+-----------+---------------------------+---------------------------------------------------------------------------------+
    | ref                            | pack      | name                      | description                                                                     |
    +--------------------------------+-----------+---------------------------+---------------------------------------------------------------------------------+
    | core.st2.webhook               | core      | st2.webhook               | Trigger type for registering webhooks that can consume arbitrary payload.       |
    | core.st2.generic.actiontrigger | core      | st2.generic.actiontrigger | Trigger encapsulating the completion of an action execution.                    |
    | core.st2.IntervalTimer         | core      | st2.IntervalTimer         | Triggers on specified intervals. e.g. every 30s, 1week etc.                     |
    | core.st2.DateTimer             | core      | st2.DateTimer             | Triggers exactly once when the current time matches the specified time. e.g.    |
    |                                |           |                           | timezone:UTC date:2014-12-31 23:59:59.                                          |
    | core.st2.CronTimer             | core      | st2.CronTimer             | Triggers whenever current time matches the specified time constaints like a     |
    |                                |           |                           | UNIX cron scheduler.                                                            |
    | core.st2.sensor.process_spawn  | core      | st2.sensor.process_spawn  | Trigger encapsulating spawning of a sensor process.                             |
    | autoscale.ScaleDownPulse       | autoscale | ScaleDownPulse            | Pulse trigger emitted when an ASG is eligible for deflation                     |
    | autoscale.ScaleUpPulse         | autoscale | ScaleUpPulse              | Pulse trigger emitted when an ASG is eligible for expansion                     |
    | slack.message                  | slack     | message                   | Trigger which indicates a new message has been posted to a channel              |
    | linux.file_watch.line          | linux     | file_watch.line           | Trigger which indicates a new line has been detected                            |
    | core.st2.sensor.process_exit   | core      | st2.sensor.process_exit   | Trigger encapsulating exit of a sensor process.                                 |
    | newrelic.WebAppAlertTrigger    | newrelic  | WebAppAlertTrigger        |                                                                                 |
    | newrelic.WebAppNormalTrigger   | newrelic  | WebAppNormalTrigger       |                                                                                 |
    | newrelic.ServerAlertTrigger    | newrelic  | ServerAlertTrigger        |                                                                                 |
    | newrelic.ServerNormalTrigger   | newrelic  | ServerNormalTrigger       |                                                                                 |
    | dripstat.alert                 | dripstat  | alert                     | Trigger representing an active alert                                            |
    +--------------------------------+-----------+---------------------------+---------------------------------------------------------------------------------+


To learn more about Sensors/Triggers, take a look at the :doc:`sensors` page.


Criteria
--------

Rule criteria are the rule(s) needed to be matched against (Logical ``AND``). Criteria in the rule is expressed as:

.. code-block:: yaml

        # more variables
        criteria:
            trigger.payload_parameter_name1:
                type: "matchregex"
                pattern : "^value$"
            trigger.payload_parameter_name2:
                type: "iequals"
                pattern : "watchevent"


``type`` specifies which criteria comparison operator to use and ``pattern`` specifies a pattern
which gets passed to the operator function.

In the ``matchregex`` case, ``pattern`` is a regular expression pattern which the trigger value
needs to match.

A list of all the available criteria operators is described below. If you are missing some
operator, you are welcome to code it up and submit a patch :)

If the criteria key contains an special characters (like ``-``) then use the dictionary lookup format for specifying
the criteria key. In case of a webhook based rule it is typical for the header of the posted event to
contain such values e.g.

.. code-block:: yaml

    criteria:
        trigger.headers['X-Custom-Header']:
            type: "eq"
            pattern : "customvalue"

The ``pattern`` value can also reference a datastore value using a Jinja
variable access syntax as shown below.

.. code-block:: yaml

    criteria:
        trigger.payload.build_number:
            type: "equals"
            pattern : "{{ system.current_build_number }}"

In this example we are referencing a value of a datastore item with the name
``current_build_number``.

Critera Comparision
-------------------

This section describes all the available operators which can be used in the criteria.

.. note::

    **For Developers:** The criteria comparision functions are defined in
    :github_st2:`st2/st2common/st2common/operators.py </st2common/st2common/operators.py>`.

===============  ===============================================================
 Operator         Description
===============  ===============================================================
``equals``       values are equal (for values of arbitrary type);
``nequals``      values are not equal (for values of arbitrary type);
``lessthan``     trigger value is less than the provided value;
``greaterthan``  trigger value is greater than the provided value;
``matchregex``   trigger value matches the provided regular expression
                 pattern;
``iequals``      string trigger value equals the provided value case
                 insensitively;
``contains``     string trigger value contains the provided value;
``ncontains``    string trigger value does not contain the provided value;
``icontains``    string trigger value contains the provided value case
                 insensitively;
``incontains``   string trigger value does not contain the provided string
                 value case insensitively;
``startswith``   beginning of the string trigger value matches the provided
                 string value;
``istartswith``  beginning of the string trigger value matches the provided
                 string value case insensitively;
``endswith``     end of the string trigger value matches the provided string
                 value;
``iendswith``    end of the string trigger value matches the provided string
                 value case insensitively;
``timediff_lt``  time difference between trigger value and current time is
                 less than the provided value;
``timediff_gt``  time difference between trigger value and current time is
                 greater than the provided value;
``exists``       key exists in payload;
``nexists``      key doesn't exist in payload.
===============  ===============================================================

Action
------

This section describes the subsequent action/workflow to be executed on a successful match of a trigger
and an optional set of criteria. At a minimum, a rule should specify the action to execute. Additionally,
a rule can also specify parameters that will be supplied to an action upon execution.


.. code-block:: yaml

        action:                                # required
            ref: "action_ref"
            parameters:                        # optional
                foo: "bar"
                baz: 1

Variable Interpolation
----------------------

Occasionally, it will be necessary to pass along context of a trigger to an action when a rule is matched.
The rules engine is able to interpolate variables by leveraging Jinja templating syntax `Jinja templating <http://jinja.pocoo.org/docs/dev/templates/>`__.

.. code-block:: yaml

        action:
            ref: "action_ref"
            parameters:
                foo: "bar"
                baz: "{{trigger.payload_parameter_1}}"


Managing Rules
--------------

To deploy a rule, use CLI ``st2 rule create ${PATH_TO_RULE}`` command, for example:

.. code-block:: bash

    st2 rule create /usr/share/doc/st2/examples/rules/sample_rule_with_webhook.yaml

If the rule with the same name already exists, the above command will return an error:

.. code-block:: bash

    ERROR: 409 Client Error: Conflict
    MESSAGE: Tried to save duplicate unique keys (E11000 duplicate key error index: st2.rule_d_b.$uid_1  dup key: { : "rule:examples:sample_rule_with_webhook" })

To update the rule, edit the rule definition file and run ``st2 rule update`` command, as in the following example:

.. code-block:: bash

    st2 rule update examples.sample_rule_with_webhook /usr/share/doc/st2/examples/rules/sample_rule_with_webhook.yaml

.. note::

    **Hint:** It is a good practice to always edit the original rule file, so that keep your infrastructure in code. You still can get the rule definition from the system by ``st2 rule get <rule name> -j``, update it, and load it back.

To see all the rules, or to get an individual rule, use commands below:

.. code-block:: bash

    st2 rule list
    st2 rule get examples.sample_rule_with_webhook

To undeploy a rule, run ``st2 rule delete ${RULE_NAME_OR_ID}``. For example, to undeploy the examples.sample_rule_with_webhook rule we deployed previously, run:

.. code-block:: bash

    st2 rule delete examples.sample_rule_with_webhook


Rule location
-------------

Custom rules must be placed in any accessible folder on local system. By convention, custom rules are placed in ``/opt/stackstorm/packs/default/rules`` directory.
By default, |st2| doesn't load the rules deployed under ``/opt/stackstorm/packs/${pack_name}/rules/``. However you can force
load them with ``st2 run packs.load register=rules`` or ``st2 run packs.load register=all``.


.. _testing-rules:

Testing Rules
-------------

To make testing the rules easier we provide a ``st2-rule-tester`` tool which allows evaluating rules against
trigger instances without running any of the StackStorm components.

The tool works by taking a path to the file which contains rule definition and a file which
contains trigger instance definition:

.. code-block:: bash

    st2-rule-tester --rule=${RULE_FILE} --trigger-instance=${TRIGGER_INSTANCE_DEFINITION}
    echo $?

Both files need to contain definitions in YAML or JSON format. For the rule, you can use the same
file you are planning to deploy.

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
      pack: "irc"
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

    st2-rule-tester --rule=./my_rule.yaml --trigger-instance=./trigger_instance_1.yaml
    echo $?

Output:

.. code-block:: bash

    === RULE MATCHES ===
    0

.. code-block:: bash

    st2-rule-tester --rule=./my_rule.yaml --trigger-instance=./trigger_instance_2.yaml
    echo $?

Output:

.. code-block:: bash

    === RULE DOES NOT MATCH ===
    1

If you are debugging and would like to see the list of trigger instances sent to |st2|,
you can use the CLI to do so.

..  code-block:: bash

  st2 triggerinstance list

You can also filter trigger instances by trigger.

.. code-block:: bash

  st2 triggerinstance list --trigger=core.f9e09284-b2b1-4127-aedd-dcde7a752819


Also, you can get trigger instances within a time range by using ``timestamp_gt`` and ``timestamp_lt`` filter
options.

.. code-block:: bash

  st2 triggerinstance list --trigger="core.f9e09284-b2b1-4127-aedd-dcde7a752819" -timestamp_gt=2015-06-01T12:00:00Z -timestamp_lt=2015-06-02T12:00:00Z

Note that you can also specify one of ``timestamp_lt`` or ``timestamp_gt`` too. You can
get details about a trigger instance by using ``get``.

.. code-block:: bash

  st2 triggerinstance get 556e135232ed35569ff23238

Something that might be useful in debugging a rule is to re-send a trigger instance into |st2|. You
can use the ``re-emit`` command for that.

.. code-block:: bash

  st2 triggerinstance re-emit 556e135232ed35569ff23238


Timers
------

Timers allow running a particular action repeatedly based on a defined time interval or one
time at a particular date and time. You can think of them as cron jobs, but with additional
flexibility, e.g. ability to run actions only once, at the provided date and time.

Currently, we support the following timer trigger types:

* ``core.st2.IntervalTimer`` - Run an action on predefined time intervals (e.g. every
  30 seconds, every 24 hours, every week, etc.).
* ``core.st2.DateTimer`` - Run an action on the specified date and time.
* ``core.st2.CronTimer`` - Run an action when current time matches the time constraint
  defined in UNIX cron format.

Timers are implemented as triggers, which means you can use them inside the rules. In the section
below, you can find some examples on how to use timers in the rule definitions.

core.st2.IntervalTimer
~~~~~~~~~~~~~~~~~~~~~~

Available attributes: ``unit``, ``delta``.
Supported values for ``unit`` attribute: ``seconds``, ``minutes``, ``hours``, ``days``,
``weeks``.

Run action every 30 seconds
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

  ---
  ...

  trigger:
    type: "core.st2.IntervalTimer"
    parameters:
        unit: "seconds"
        delta: 30

  action:
    ...

Run action every 24 hours
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

  ---
  ...

  trigger:
    type: "core.st2.IntervalTimer"
    parameters:
        unit: "hours"
        delta: 24

  action:
    ...

Run action every 2 weeks
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

  ---
  ...

  trigger:
    type: "core.st2.IntervalTimer"
    parameters:
        unit: "weeks"
        delta: 2

  action:
    ...

core.st2.DateTimer
~~~~~~~~~~~~~~~~~~

Available attributes: ``timezone``, ``date``.

Run action on a specific date
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

  ---
  ...

  trigger:
    type: "core.st2.IntervalTimer"
    parameters:
        timezone: "UTC"
        date: "2014-12-31 23:59:59"

  action:
    ...

core.st2.CronTimer
~~~~~~~~~~~~~~~~~~

Available attributes: ``timezone``, ``year``, ``month``, ``day``, ``week``, ``day_of_week``,
``hour``, ``minute``, ``second``.

Run action every sunday at midnight
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

  ---
  ...

  trigger:
    type: "core.st2.CronTimer"
    parameters:
        timezone: "UTC"
        day_of_week: 6
        hour: 0
        minute: 0
        second: 0

  action:
    ...

-------------------------------

.. rubric:: What's Next?

* Explore automations on `st2contrib`_ community repo.
* Learn more about :doc:`sensors`.
* Check out `tutorials on stackstorm.com <http://stackstorm.com/category/tutorials/>`__ - a growing set of practical examples of automating with StackStorm.


.. include:: __engage.rst
