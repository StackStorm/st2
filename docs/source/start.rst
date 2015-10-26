Quick Start
=================

Got |st2| :doc:`installed </install/index>`? Enjoyed :doc:`the intro video <video>`? Let's give 
it a try. This guide will walk you through |st2| basics and help you build and run a simple 
automation: a rule that triggers an action on external event.


Explore |st2| with CLI
----------------------------
The best way to explore |st2| is to use CLI. Start by firing a few commands:

.. code-block:: bash

    st2 --version

    # Get help. It's a lot. Explore.
    st2 -h

    # Authenticate and export the token. Make sure ST2_AUTH_URL and 
    # ST2_API_URL are set correctly (http vs https, endpoint, and etc).
    # Replace the username and password in the example below appropriately.
    export ST2_AUTH_TOKEN=`st2 auth -t -p pass123 admin`

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

The default “all-in-one” installation deploys the CLI along with the |st2| services. CLI can be 
used to access |st2| service remotely. All |st2| operations are also available via REST API, 
Python, and JavaScript bindings. Check the :doc:`CLI and Python Client </reference/cli>` reference 
for details.

From v0.8, |st2| ships with WebUI. With the default "all-in-one" installation, you can access it at
https://hostname_or_ip or http://hostname_or_ip if SSL is not configured.

Authenticate
------------
If :doc:`authentication <authentication>` is enabled, obtain authentication token with 
``st2 auth <username>``, and supply the token to each st2 command using the ``--token`` or ``-t``
parameter. For convenience, keep the credential in the CLI config file, or set the environment 
variable ``ST2_AUTH_TOKEN``. When using environment variable, make sure that ``ST2_API_URL`` and 
``ST2_AUTH_URL`` are set appropriately. The doc section on authentication 
:ref:`usages <authentication-usage>` contains additional notes. A nice shortcut for now is:

.. code-block:: bash

    export ST2_AUTH_TOKEN=`st2 auth -t -p pass123 admin`


Work with Actions
-----------------

|st2| comes with a several generic actions out of the box. The catalog of actions can be easily
extended by getting actions from the community or consuming your existing scripts (`more on that
later`). Browse the catalog with ``st2 action list``. Action is referred to by `ref` as 
``pack.action_name`` (e.g. ``core.local``). Learn about an action by doing 
``st2 action get <action>``, or, ``st2 run <action> --h (--help)``: the command shows the
description along with action parameters so that you know how to run it from the CLI or use it
in rules and workflows.

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
    st2 run -j core.http url="http://docs.stackstorm.com" method="GET"

Use ``core.remote`` action to run linux command on multiple hosts over ssh. This assumes that 
passwordless SSH access is configured for the hosts, as described in :ref:`config-configure-ssh` 
section.

.. code-block:: bash

    st2 run core.remote hosts='abc.example.com, cde.example.com' username='mysshuser' -- ls -l

.. note::

    For ``core.local`` and ``core.remote`` actions, we use ``--`` to separate action parameters
    to ensure that options keys, like ``-l`` or ``-a`` are properly passed to the action. 
    Alternatively, ``core.local`` and ``core.remote`` actions take the ``cmd`` parameter to pass 
    crazily complex commands.

    When specifying a command using the command line tool, you also need to escape all the
    variables, otherwise the variables will get interpolated locally by a shell. Variables
    are escaped using a backslash (``\``) - e.g.
    `\\$user`.

.. code-block:: bash

    # Using `--` to separate arguments
    st2 run core.local -- ls -al

    # Equivalent using `cmd` parameter
    st2 run core.local cmd="ls -al"

    # Crazily complex command passed with `cmd`
    st2 run core.remote hosts='localhost' cmd="for u in bob phill luke; do echo \"Logins by \$u per day:\"; grep \$u /var/log/secure | grep opened | awk '{print \$1 \"-\" \$2}' | uniq -c | sort; done;"

Check the action execution history and details of action executions with ``st2 execution`` command:

.. code-block:: bash

    # List of executions (recent at the bottom)
    st2 execution list

    # Get execution by ID
    st2 execution get <execution_id>

    # Get only the last 5 executions
    st2 execution list -n 5

That's it. You have learned to run |st2|'s actions. Let's stitch together other automation.


Define a Rule
-------------

|st2| uses rules to fire actions or workflows when events happen. Events are typically monitored i
by sensors. When a sensor catches an event, it fires a trigger. Trigger trips the rule, the rule 
checks the criteria and if it matches, it runs an action. Easy enough. Let’s look at an example.

Sample rule: :github_st2:`sample_rule_with_webhook.yaml
<contrib/examples/rules/sample_rule_with_webhook.yaml>` :

.. literalinclude:: /../../contrib/examples/rules/sample_rule_with_webhook.yaml
    :language: yaml

The rule definition is a YAML with three sections: trigger, criteria, and action. This example is
setup to react on a webhook trigger and applies filtering criteria on the content of the trigger.
The webhook in this example is setup to listen on the ``sample`` sub-url at 
``https://{host}:9101/v1/webhooks/sample``. When a POST is made on this URL, the trigger
fires. If the criteria matches, value in payload is ``st2`` in this case, the payload will be
appended to the file st2.webhook_sample.out in the home directory of the user setup to run |st2|.
By default, ``stanley`` is the default user and the file will be located at 
``/home/stanley/st2.webhook_sample.out``. See :doc:`rules` for detailed rule anatomy.

Trigger payload is referred with ``{{trigger}}``. If the trigger payload is a valid JSON,
it is parsed and can be accessed like ``{{trigger.path.to.parameter}}`` (it's
`Jinja template syntax <http://jinja.pocoo.org/docs/dev/templates/>`__).

What are the triggers available to use in rules? Just like with actions, use the CLI to browse
triggers, learn what the trigger does, how to configure it, and what is it’s payload structure:

.. code-block:: bash

    # List all available triggers
    st2 trigger list

    # Check details on Interval Timer trigger
    st2 trigger get core.st2.IntervalTimer

    # Check details on the Webhook trigger
    st2 trigger get core.st2.webhook

Deploy Rule
-----------

|st2| can be configured to auto-load the rules or rules can be deployed with API or CLI:

.. code-block:: bash

    # Create the rule
    st2 rule create /usr/share/doc/st2/examples/rules/sample_rule_with_webhook.yaml

    # List the rules
    st2 rule list

    # List the rules for the examples pack
    st2 rule list --pack=examples

    # Get the rule that was just created
    st2 rule get examples.webhook_file

Once the rule is created, the webhook begins to listen on ``https://{host}:9101/v1/webhooks/{url}``.
Fire the POST, check out the file and see that it appends the payload if the name=Joe.

.. code-block:: bash

    # Post to the webhook
    curl -k https://localhost:9101/v1/webhooks/sample -d '{"foo": "bar", "name": "st2"}' -H 'Content-Type: application/json' -H 'X-Auth-Token: put_token_here'

    # Check if the action got executed (this shows last action)
    st2 execution list -n 1

    # Check that the rule worked. By default, st2 runs as the stanley user.
    sudo tail /home/stanley/st2.webhook_sample.out

    # And for fun, same post with |st2|
    st2 run core.http method=POST body='{"you": "too", "name": "st2"}' url=https://localhost:9101/v1/webhooks/sample headers='x-auth-token=put_token_here;content-type=application/json' verify_ssl_cert=False

    # Check that the rule worked. By default, st2 runs as the stanley user.
    sudo tail /home/stanley/st2.webhook_sample.out

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

Datastore
---------

While the most data are retrieved as needed by |st2|, you may need to store and share some common 
variables. Use |st2| datastore service to store the values and reference them in rules and workflows
as ``{{system.my_parameter}}``. This creates ``user=stanley`` key-value pair:

.. code-block:: bash

    # Create a new key value pair
    st2 key set user stanley

    # List the key value pairs in the datastore
    st2 key list

For more information on datastore, check :doc:`datastore`

Troubleshooting
----------------------
If something goes wrong, follow :doc:`/troubleshooting/index` guide, and engage with developers at
the community channel on slack at `stackstorm-community.slack.com <https://stackstorm-community.slack.com>`__.


-------------------------------

.. rubric:: What's Next?

* Get more actions, triggers, rules:


    * Install integration packs from `st2contrib`_  - follow guide on :doc:`/packs`.
    * :ref:`Convert your scripts into StackStorm actions. <ref-actions-converting-scripts>`
    * Learn how to :ref:`write custom actions <ref-actions-writing-custom>`.

* Use workflows to stitch actions into higher level automations - :doc:`/workflows`.
* Check out `tutorials on stackstorm.com <http://stackstorm.com/category/tutorials/>`__ - a growing set of practical examples of automating with StackStorm.


.. include:: engage.rst

