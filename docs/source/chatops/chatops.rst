.. _ref-chatops:

What is ChatOps
===============

ChatOps is a new operational paradigm where work that is already
happening in the background today is brought into a common chatroom. By
doing this, you are unifying the communication about what work should
get done with actual history of the work being done. Things like
deploying code from chat, viewing graphs from a TSDB or logging tool, or
creating new Jira tickets... all of these are examples of tasks that can
be done via ChatOps.

Not only does ChatOps reduce the feedback loop of work output, it also
empowers others to accomplish complex self-service tasks that they
otherwise would not be able to do. Combining ChatOps and StackStorm is
an ideal combination, where from Chat users will be able to execute
actions and workflows to accelerate the IT delivery pipeline.

.. _chatops-configuration:

Configuration
=============

All-in-one installer
~~~~~~~~~~~~~~~~~~~~

If you used the :doc:`/install/all_in_one` and configured ChatOps through that then we
have already setup ChatOps for you so you can move to the next section.


Manual Installation
~~~~~~~~~~~~~~~~~~~

To get started, you will need:

-  StackStorm v0.11.0 or higher
-  Hubot
-  StackStorm Hubot adapter


Instructions on how to configure and deploy Hubot for your platform can be found
`here <https://hubot.github.com/docs/deploying/>`__. Also ensure it is
configured to connect to your chat service of choice. You can find
documentation for this at
https://github.com/github/hubot/blob/master/docs/adapters.md.

Finally, you need to install and configure StackStorm Hubot plugin. For
information on how to do that, please visit the following page -
`Installing and configuring the
plugin <https://github.com/stackstorm/hubot-stackstorm#installing-and-configuring-the-plugin>`__.

If you are installing Hubot on a machine that is not the same as your
StackStorm installation, you will need to set the following environment
variables:

-  ``ST2_API`` - FQDN + port to StackStorm endpoint. Typically:
   ``http://<host>:9101``
-  ``ST2_AUTH_URL`` - FQDN + port to StackStorm Auth endpoint:
   ``http://<host>:9100``
-  ``ST2_AUTH_USERNAME`` - StackStorm installation username
-  ``ST2_AUTH_PASSWORD`` - StackStorm installation password

Once done, start up your Hubot instance. Validate that things are
working alright and Hubot is connecting to your client by issuing a
default command. For example, if you named your Hubot instance
``frybot``, you can issue the command:

::

      frybot: the rules

And should get something like this back:

.. figure:: /_static/images/chatops_the_rules.png

Now, install the ``hubot`` pack into your StackStorm installation.

::

      $ st2 run packs.install packs=hubot,st2

If successful, proceed to the next section.

Adding new ChatOps commands
===========================

ChatOps uses :doc:`Action aliases </aliases>` to define new ChatOps commands.

::

    $ cd /opt/stackstorm/packs/
    $ mkdir -p chatops/{actions,rules,sensors,aliases}

Now, let's configure an alias and setup an action to be used in ChatOps.
For this example, let's download a pack from our ``st2contrib``
repository, the Google pack. This will provide us with the action
``google.get_search_results`` that we will expose via ChatOps. To install the pack

::

    $ st2 run packs.install packs=google

Now, let's setup an alias. For purpose of this setup aliases are stored
in the directory ``/opt/stackstorm/packs/chatops/aliases`` on the
filesystem. We have already created this directory in a previous step.
Create a new file called ``google.yaml``, and add the following
contents.

.. code:: yaml

    # packs/chatops/aliases/google.yaml
    ---
    name: "google_query"
    description: "Perform a google search"
    action_ref: "google.get_search_results"
    formats:
      - "google {{query}}"

Now, once this is all done, register all the new files we created and
reload Hubot. Do this with the following commands:

::

    $ sudo st2ctl reload
    $ sudo service hubot restart

This will register the aliases we created, and tell Hubot to go and
refresh its command list.

You should now be able to go into your chatroom, and execute the command
``hubot: google awesome``, and StackStorm will take care of the rest.

.. figure:: /_static/images/chatops_command_out.png
