Traces
======

Traces are tracking entities that serve to gather all |st2| entities, like ActionExecution,
TriggerInstance and Rule, that are cascades from a shared origin.

Examples
--------

Let us walk through a couple of canonical cases -

External events
^^^^^^^^^^^^^^^

TriggerInstance(ti1) dispatched by Sensor to |st2|, matched a Rule(r1) leading to an ActionExecution(ae1). On completion of ae1 an ActionTrigger TriggerInstance(ti2) is dispatched by |st2|.

The trace created in this case contains all the entities from above since they cascade
from the same origin i.e. TriggerInstance(ti1) dispatched into the system.

.. code-block:: bash

   Trace
     |- ti1
     |- r1
     |- ae1
     |- ti2

Connected flows
^^^^^^^^^^^^^^^

Since |st2| raises an internal ActionTrigger it is possible for rules to be used in conjunction with those on completion of executions.

ActionExecution(ae1) started by user, on completion of ae1 an ActionTrigger TriggerInstance(ti1) is dispatched, Rule(r1) matches and leads to ActionExecution(ae2) another ActionTrigger TriggerInstance(ti2) is dispatched but no rule matched.

The trace created in this case contains all the entities from above since they cascade
from the same origin i.e. ActionExecution(ae1) dispatched into the system.

.. code-block:: bash

   Trace
     |- ae1
     |- ti1
     |- r1
     |- ae2
     |- ti2


Tracing Triggers and Executions
-------------------------------

It is possible for users to define identifying information for a Trace at injection points. There are 2 injection points for |st2| where a Trace can start -

* Dispatch a Trigger (more precisely this is dispatching a TriggerInstance)
* Execute an Action (aka creation of an ActionExecution)

What is a trace_tag and trace_id?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``trace-tag`` : User specified and therefore friendly way to tag a Trace. There is no requirement for this value to be unique and |st2| will not enforce this either. Whenever only a trace-tag is provided at one of the injection points a new Trace is started.

* ``trace-id`` : This is a |st2| defined value and is guaranteed to be unique. Users can specify this value at the injection point but a Trace with the specified trace-id must already exist.

Dispatch a Trigger
^^^^^^^^^^^^^^^^^^

TriggerInstance dispatch most often happens from a Sensor. The :ref:`authoring a sensor<ref-sensors-authoring-a-sensor>` page contains information on how to introduce a Trace.

A brief snippet is included here to explain some trace specific constructs. A sensor would inject such triggers by using the sensor\_service passed into the sensor on instantiation.

.. code-block:: python

    self._sensor_service.dispatch(trigger=trigger, payload=payload, trace_tag=trace_tag)


Here the Sensor is expected to supply a meaningful value for ``trace_tag`` e.g.

* Commit SHA of a git commit for a git commit hook trigger.
* Id of the event from a monitoring system, like Sensu or Nagios, that is relayed to |st2|.

Execute an Action
^^^^^^^^^^^^^^^^^

Execution of an Action can also be assocaited with a Trace. Here is how this could be done from the CLI.

To start a new trace use ``trace-tag``

.. code-block:: bash

   $ st2 run core.local date --trace-tag TraceDateAction


To associate with an existing trace use ``trace-id``

.. code-block:: bash

   $ st2 run core.local uname --trace-id 55d505fd32ed35711522c4c8


Viewing Trace
-------------

|st2| CLI provides the ability to list and get traces.


List
^^^^

* All traces in the system

.. code-block:: bash

    $ st2 trace list


* Filter by trace-id

.. code-block:: bash

    $ st2 trace list --trace-tag <trace-tag>

* Filter by execution

.. code-block:: bash

    $ st2 trace list --execution 55d505fd32ed35711522c4c7

* Filter by rule

.. code-block:: bash

    $ st2 trace list --rule 55d5064432ed35711522c4ca

* Filter by trigger-instance

.. code-block:: bash

    $ st2 trace list --trigger-instance 55d5069832ed35711cc4b08e


Get
^^^

* Get a specific trace

.. code-block:: bash

    $ st2 trace get <trace-id>

* View the causation chain in a trace for an action execution. Similarly for rule and trigger-instance.

.. code-block:: bash

    $ st2 trace get <trace-id> -e

* View specific type in a trace.

.. code-block:: bash

    $ st2 trace get <trace-id> --show-executions

* Hide noop trigger instances. These are trigger instances which do no lead to a rule enforcement.

.. code-block:: bash

    $ st2 trace get <trace-id> --hide-noop-triggers


Is everythign traced?
---------------------

By default all ActionExecutions and TriggerInstances are traced. If no ``trace-tag`` is provided by a user then |st2| automatically generate a ``trace-tag`` to provide tracking.
