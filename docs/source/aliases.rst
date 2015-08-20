Action Alias
============

Alias for an action in StackStorm. A simplified and more human readable representation
of actions in StackStorm which are useful in text based interfaces like ChatOps.

For now ActionAlias is only leveraged via ChatOps clients.

Action Alias Structure
^^^^^^^^^^^^^^^^^^^^^^

Action aliases are content like actions, rules and sensors. They are also defined in yaml
files and deployed via packs.

e.g.

.. code-block:: yaml

    ---
    name: "google_query"
    description: "Perform a Google Query"
    action_ref: "google.get_search_results"
    formats:
      - "google {{query}}"


In the above example ``google_query`` is an alias for ``google.get_search_results`` action. The
supported format for the alias is specified in the ``formats`` field. A single alias can support
multiple formats for the same action.

Property description
~~~~~~~~~~~~~~~~~~~~

1. name : unique name of the alias.
2. action_ref : reference to the action that is being aliased.
3. formats : possible options for user to invoke action. Typically specified by the user in a textual
             interface as supported by ChatOps.

Location
~~~~~~~~

Action Aliases are supplied in packs as yaml files.

.. code-block:: bash

    packs/my_pack$ ls
    actions  aliases  rules  sensors

Each alias is a single yaml file with the alias and supporting multiple formats.

Loading
~~~~~~~

When a pack is registered the aliases are not automatically loaded. To load all aliases use -

.. code-block:: bash

   st2ctl reload --register-aliases


Supported formats
^^^^^^^^^^^^^^^^^

Aliases support following format structures.

Basic
~~~~~

.. code-block:: yaml

    formats:
      - "google {{query}}"


In this case if user were to provide ``google StackStorm``, via a ChatOps interface, the aliasing mechanism
would interpret ``query = StackStorm``. The action ``google.get_search_results`` would be called with the
parameters -

.. code-block:: yaml

   parameters:
       query: StackStorm

With default
~~~~~~~~~~~~

Using example -

.. code-block:: yaml

    formats:
      - "google {{query=StackStorm}}"

In this case the query has a default value assigned which will be used if not value is provided by user.
Therefore,  simple ``google`` instead of ``google StackStorm`` would still result in assumption of the
default value much like how an Action default parameter values are interpretted.


Key-Value parameters
~~~~~~~~~~~~~~~~~~~~

Using example -

.. code-block:: yaml

    formats:
      - "google {{query}}"

It is possible to supply extra key value parameters like ``google StackStorm limit=10``. In this case even
though ``limit`` does not appear in any alias format it will still be extracted and supplied for execution.
In this the action google.get_search_results would be called with the parameters -

.. code-block:: yaml

   parameters:
       query: StackStorm
       limit: 10

Multiple formats in single alias
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A single alias file allow multiple formats to be specified for a single alias e.g.

.. code-block:: yaml

    ---
    name: "st2_sensors_list"
    action_ref: "st2.sensors.list"
    description: "List available StackStorm sensors."
    formats:
        - "list sensors"
        - "list sensors from {{ pack }}"
        - "sensors list"

The above alias supports the following commands -

.. code-block:: bash

    !sensors list
    !list sensors
    !sensors list pack=examples
    !list sensors from examples
    !list sensors from examples limit=2

ChatOps
^^^^^^^

To see how to use aliases with your favorite Chat client and implement ChatOps in your infrastructure
go `here <https://github.com/StackStorm/st2/blob/master/instructables/chatops.md>`_.

