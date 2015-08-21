Quick Start
=================

Got |st2| :doc:`installed </install/index>`? Enjoyed
:doc:`the intro video <video>`? Let's give it a try.
This guide will walk you through |st2| basics and help you build and run
a simple automation: a rule that triggers an action on external event.


Explore |st2| with CLI
----------------------------
The best way to explore |st2| is to use CLI. Start by firing a few commands:

.. code-block:: bash

    st2 --version
    # Get help. It's a lot. Explore.
    st2 -h
    # Authenticate and export the token
    export ST2_AUTH_TOKEN=`st2 auth -t -p testp testu`
    # List the actions from a 'core' pack
    st2 action list --pack=core
    st2 trigger list
    st2 rule list
    # Run a local shell command
    st2 run core.local -- date -R
    # See the execution results
    st2 execution list
    # Fire a shell comand on remote hosts. Requires passwordless SSH configured.
    st2 run core.remote hosts='localhost' -- uname -a

The default “all-in-one” installation deploys the CLI along with the |st2|
services. CLI can be used to access |st2| service remotely. All |st2|
operations are also available via REST API, Python, and JavaScript bindings.
Check the :doc:`CLI and Python Client </reference/cli>` reference for details.

From v0.8, |st2| ships with WebUI. With the default "all-in-one" installation, you can access it at
http://hostname:8080/.

Authenticate
----------------
If :doc:`authentication </authentication>` enabled, obtain authentication token with ``st2 auth <username>``,
and supply it with each command using ``--token`` parameter. For convenience,
keep credentials in CLI config file, or put it to environment variable ``ST2_AUTH_TOKEN``.
:ref:`Details here <authentication-usage>`, a nice shortcut for now is:

.. code-block:: bash

    export ST2_AUTH_TOKEN=`st2 auth -t -p testp testu`


Work with Actions
---------------------

|st2| comes with a several generic actions out of the box.
Action Library can be easily extended by getting actions from the community or consuming
your existing scripts (`more on that later`). Browse Action Library with
``st2 action list``. Action is called by `ref` as ``pack.action_name``
(e.g. ``core.local``). Learn about an action by doing
``st2 action get <action>``, or, ``st2 run <action> --h ( --help)``: it shows
description along with action parameters so that you know how to run it
from the CLI or use it in rules and workflows.


.. code-block:: bash

    # List all the actions in the library
    st2 action list
    # Get action metadata
    st2 action get core.http
    # Display action details and parameters.
    st2 run core.http --help

To run the action from the CLI, do
``st2 run <action> key=value positional arguments``.

.. code-block:: bash

    # Run a local command
    st2 run core.local -- uname -a

    # HTTP REST call to st2 action endpoint
    st2 run -j core.http url="http://localhost:9101/v1/actions" method="GET"

Use ``core.remote`` action to run linux command on multiple hosts over ssh.
This assumes that passwordless SSH access is configured for the hosts,
as described in :ref:`config-configure-ssh` section.

.. code-block:: bash

    st2 run core.remote hosts='abc.example.com, cde.example.com' username='mysshuser' -- ls -l

.. note::

    For ``core.local`` and ``core.remote`` actions, we use ``--`` to separate action
    parameters to ensure that options keys, like ``-l`` or ``-a`` are
    properly passed to the action. Alternatively, ``core.local`` and ``core.remote`` actions take
    the ``cmd`` parameter to pass crazily complex commands.

    When specifying a command using the command line tool, you also need to escape all the
    variables, otherwise the variables will get interpolated locally by a shell. Variables
    are escaped using a backslash (``\``) - e.g.
    `\\$user`.

.. code-block:: bash

    # Using `--` to separate arguments
    st2 run core.local -- ls -al
    # Equivalent using `cmd` parameter
    st2 run core.local cmd="ls -al"
    # Crasily complex command passed with `cmd`
    st2 run core.remote hosts='localhost' cmd="for u in bob phill luke; do echo \"Logins by \$u per day:\"; grep \$u /var/log/secure | grep opened | awk '{print \$1 \"-\" \$2}' | uniq -c | sort; done;"

Check the action execution history and details of action executions with ``st2 execution`` command:

.. code-block:: bash

    # List of executions (recent at the bottom)
    st2 execution list
    # Get execution by ID
    st2 execution get <execution_id>
    # Get the output of just the last execution
    st2 execution list -n 1

That's it. You have learned to use |st2|'s action library. Let's proceed to automations.


Define a Rule
-------------------------

|st2| uses rules to fire actions or workflows when events happen.
Events are typically monitored by sensors. When a sensor catches an event,
it fires a trigger. Trigger trips the rule, the rule checks the criteria
and if it matches, it runs an action. Easy enough. Let’s look at an example.

Sample rule: :github_st2:`sample_rule_with_webhook.yaml
<contrib/examples/rules/sample_rule_with_webhook.yaml>` :

.. literalinclude:: /../../contrib/examples/rules/sample_rule_with_webhook.yaml
    :language: yaml


The rule definition is a YAML spec with three sections: trigger, criteria, and action.
It configures the webhook trigger with url, applies filtering criteria based trigger
parameters. This one configures a webhook with ``sample`` sub-url so it listens
on ``http://{host}:9101/v1/webhooks/sample``.
When it fires, it appends a payload to the file, only if the ``name``
value in payload is ``st2``. See :doc:`rules` for detailed rule anatomy.

Trigger payload is referred with ``{{trigger}}``. If trigger payload is valid JSON,
it is parsed and can be accessed like ``{{trigger.path.to.parameter}}`` (it's
`Jinja template syntax <http://jinja.pocoo.org/docs/dev/templates/>`__).

What are the triggers availabe to use in rules? Just like with actions,
use the CLI to browse triggers, learn what the trigger does,
how to configure it, and what is it’s payload structure:

.. code-block:: bash

    # List all available triggers
    st2 trigger list

    # Check details on Interval Timer trigger
    st2 trigger get core.st2.IntervalTimer

    # Check details on the Webhook trigger
    st2 trigger get core.st2.webhook


Datastore
-------------------------

While the most data are retrieved as needed by |st2|, you may need to
store and share some common variables. Use |st2| datastore service to store
the values and reference them in rules and workflows
as ``{{system.my_parameter}}``. This creates ``user=stanley`` key-value pair:

.. code-block:: bash

    st2 key set user stanley
    st2 key list

For more information on datastore, check :doc:`datastore`

Deploy a Rule
-------------------------

|st2| can be configured to auto-load the rules,
or they are deployed with API or CLI:

.. code-block:: bash

    st2 rule create /usr/share/doc/st2/examples/rules/sample_rule_with_webhook.yaml
    st2 rule list
    st2 rule get examples.webhook_file

Once the rule is created, the webhook begins to listen on
``http://{host}:9101/v1/webhooks/{url}``. Fire the post, check out
the file and see that it appends the payload if the name=Joe.

.. code-block:: bash

    # Post to the webhook
    curl http://localhost:9101/v1/webhooks/sample -d '{"foo": "bar", "name": "st2"}' -H 'Content-Type: application/json'
    # Check if the action got executed (this shows last action)
    st2 execution list -n 1
    # Check that the rule worked
    tail /tmp/st2.webhook_sample.out
    # And for fun, same post with |st2|
    st2 run core.http method=POST body='{"you": "too", "name": "st2"}' url=http://localhost:9101/v1/webhooks/sample
    # Check that the rule worked again
    tail /tmp/st2.webhook_sample.out

Congratulations, your first |st2| rule is up and running!

 .. _start-deploy-examples:

Deploy Examples
-------------------------
Examples of rules, custom sensors, actions, and workflows are installed with |st2| and located
at :github_st2:`/usr/share/doc/st2/examples <contrib/examples/>`. To deploy, copy them
to /opt/stackstorm/packs/, setup, and reload the content:

.. code-block:: bash

    # Copy examples to st2 content directory
    sudo cp -r /usr/share/doc/st2/examples/ /opt/stackstorm/packs/

    # Run setup
    st2 run packs.setup_virtualenv packs=examples

    # Reload stackstorm context
    st2ctl reload --register-all

For more content - actions, sensors, rules - checkout `st2contrib`_ community repo on GitHub.


Troubleshooting
----------------------
If something goes wrong, follow :doc:`/troubleshooting` guide, and engage with developers at `#stackstorm on irc.freenode.org <http://webchat.freenode.net/?channels=stackstorm>`__


-------------------------------

.. rubric:: What's Next?

* Get more actions, triggers, rules:


    * Install integration packs from `st2contrib`_  - follow guide on :doc:`/packs`.
    * :ref:`Convert your scripts into StackStorm actions. <ref-actions-converting-scripts>`
    * Learn how to :ref:`write custom actions <ref-actions-writing-custom>`.

* Connect with your monitoring system - :doc:`resources/monitoring`.
* Use workflows to stitch actions into higher level automations - :doc:`/workflows`.

* Check out `tutorials on stackstorm.com <http://stackstorm.com/category/tutorials/>`__ - a growing set of practical examples of automating with StackStorm.


.. include:: engage.rst

