Action Alias
============

Action Alias is a simplified and more human readable representation
of actions in StackStorm which are useful in text based interfaces, notably ChatOps.

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

Listing
~~~~~~~

To list all currently registered action aliases, use -

.. code-block:: bash

   st2 action-alias list

Loading
~~~~~~~

When a pack is registered the aliases are not automatically loaded. To load all aliases use -

.. code-block:: bash

   st2ctl reload --register-aliases

Removing
~~~~~~~~

When you like to remove an action alias, use -

.. code-block:: bash

   st2 action-alias delete ALIAS



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

Regular expressions
~~~~~~~~~~~~~~~~~~~

It is possible to use regular expressions in the format string:

.. code-block:: yaml

    formats:
      - "(google|look for) {{query=StackStorm}}[!.]?"

They can be as complex as you want, just exercise reasonable caution as regexes tend to be difficult to debug.

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

Additional ChatOps parameters passed to the command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An execution triggered via chatops will contain variables such as ``action_context.api_user``, ``action_context.user`` and ``action_context.source_channel``. ``api_user`` is the user who's kicking off the chatops command from
client and ``user`` is the |st2| user configured in hubot. ``source_channel`` is the channel
in which the chatops command was kicked off.

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

"Display-representation" format objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, every format string is exposed in Hubot help as is. This is not always desirable in case you want to make a complicated regex, have ten very similar format strings to "humanize" the input, or hide one of the strings for any other reason.

In this case, instead of having a string in `formats`, you can write an object with a `display` parameter (a string that will show up in help) and a `representation` list (matches that Hubot will actually look for):

.. code-block:: yaml

    formats:
      - display: "google {{query}}"
        representation:
          - "(google|look for) {{query=StackStorm}}[!.]?"
          - "search google for {{query}}"

This will work as follows:

  - the `display` string (`google {{query}}`) will be exposed via the `!help` command.
  - strings from the `representation` list (`(google|look for) {{query=StackStorm}}[!.]?` regex, and `search google for {{query}}` string) will be matched by Hubot.

You can use both strings and display-representation objects in `formats` at the same time:

.. code-block:: yaml

    formats:
      - display: "google {{query}}"
        representation:
          - "(google|look for) {{query=StackStorm}}[!.]?"
          - "search google for {{query}}"
      - "find me some {{query}}"
      - "find me some {{query}} in {{engine}}"

Acknowledgement options
^^^^^^^^^^^^^^^^^^^^^^^

Hubot will acknowledge every ChatOps command with a random message containing StackStorm execution ID and a link to the Web UI. It's possible to customize this message in your alias definition:

.. code-block:: yaml

    ack:
      format: "acknowledged!"
      append_url: false

The `format` parameter will customize your message, and the `append_url` flag controls the Web UI link at the end. It is also possible to use Jinja in the format string, with `actionalias` and `execution` comprising the Jinja context:

.. code-block:: yaml

    ack:
      format: "Executing `{{ actionalias.ref }}`, your ID is `{{ execution.id[:2] }}..{{ execution.id[-2:] }}`"

The `enabled` parameter controls whether the message will be sent. It defaults to `true`, and setting it to `false` will disable the acknowledgement message altogether:

.. code-block:: yaml

    ack:
      enabled: false

Result options
^^^^^^^^^^^^^^

Same as with `ack`, you can configure `result` to disable result messages or set a custom format so that Hubot would output a nicely formatted list, filter strings, or switch the message text depending on execution status:

.. code-block:: yaml

    result:
      format: |
        {% if execution.result.result|length %}
        found something for you:
        {% for article in execution.result.result %}
        {{ loop.index }}. *{{ article.title }}*: {{ article.url }}
        {% endfor %}
        {% else %}
        couldn't find anything, sorry!
        {% endif %}

To disable the result message, you can use the `enabled` flag same way as in `ack`.

Plaintext/attachment (slack-only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Slack uses attachments to format the result message. While we found attachments to be the best way to handle very long messages (which StackStorm execution results tend to be), sometimes you want part of your message — or all of it — in plaintext. Use `{~}` as a delimiter to do that:

.. code-block:: yaml

    result:
      format: "action completed! {~} {{ execution.result.result }}"

In this case "action completed!" will be output in plaintext, and the execution result will follow as attachment.

`{~}` can also be put at the end of the string to output the whole message in plaintext.

ChatOps
^^^^^^^

To see how to use aliases with your favorite Chat client and implement ChatOps in your infrastructure
go `here <https://github.com/StackStorm/st2/blob/master/instructables/chatops.md>`_.



