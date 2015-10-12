Notifications
=============

If you read through :ref:`ref-chatops` section, you are familiar with notifications.
Even without chatops, notifications can be used to post messages to external systems
like chat clients, send emails etc. Notifications require an action that is registered with
st2 (For example, ``slack`` pack contains a
`post_message <https://github.com/StackStorm/st2contrib/blob/master/packs/slack/actions/post_message.yaml>`_ action.)
and a notification rule to go with it. Notifications are implemented as triggers and rules and actions.
A speical ``core.st2.notifytrigger`` is emitted by the system on completion of every action
and a rule to match the trigger to a notify action results in notifications being sent out.

How to setup a notification for a simple action?
------------------------------------------------

This is the easiest case. You can do this by specifying a ``notify`` section in the YAML meta
while registering the action. For example:

::

    ---
    description: Action that executes an arbitrary Linux command on the localhost.
    enabled: true
    entry_point: ''
    name: local-notify
    notify:
      on-complete:
        routes:
        - slack
        message: '"@channel: Action succeeded."'
    parameters:
      cmd:
        description: Arbitrary Linux command to be executed on the remote host(s).
        required: true
        type: string
      sudo:
        immutable: true
    runner_type: "local-shell-cmd"

Above is the same action as a ``local-shell-cmd`` action but with notify. As you can see, there
is a notify section with ``on-complete`` section. You can also specify `on-success`
and ``on-failure`` sections with different messages. These subsections are all optional but at
least one is required for any meaningful notification. For sake of clarity, an ``on-success`` case
is presented below.


::

   notify:
      on-complete:
        routes:
        - slack
        message: '"@channel: Action succeeded."'
      on-success:
        routes:
        - slack
        message: '"@channel: Woohoo!"'

The message doesn't support jinja templating yet. This support will be added in the future.
Also, when the notification triggers are sent out, the message supplied along with a ``data``
field containing the results of the execution are sent out. The rule can use these two fields -
``message`` and ``data`` - and send it out as part of the action.

How to write a rule for notification?
-------------------------------------

The rule to tie a st2 registered ``notify`` action resembles the notify rule you are familiar
with when you setup chatops. An example is below:

::

    ---
    name: "sample.notify_slack"
    pack: "examples"
    description: "Sample rule firing on action completion."
    enabled: true

    trigger:
      type: "core.st2.generic.notifytrigger"
      parameters: {}
    criteria:
      trigger.channel:
        pattern: "slack"
        type: "equals"
    action:
      ref: "slack.post_message"
      parameters:
        message: "{{trigger.message}}"

As you can see, this rule is setup for notification route ``slack``. The action section shows
that ``slack.post_message`` is the one what would be kicked off. We are skipping the ``data`` part
of the trigger for brevity. If you had a slack action that also consumed some data as JSON string,
you could pass ``data: "{{data}}"`` as a parameter. Again, selecting specific fields from the
output (via jinja) is not supported yet.

How do I setup notifications in action chain?
---------------------------------------------

The procedure here is the same if you want the same notify for all tasks in the chain. You would
register an action meta with notify section. For example:

::

    ---
    # Action definition metadata
    name: "echochain"
    description: "Simple Action Chain workflow"

    # `runner_type` has value `action-chain` to identify that action is an ActionChain.
    runner_type: "action-chain"

    # `entry_point` path to the ActionChain definition file, relative to the pack's action directory.
    entry_point: "chains/echochain.yaml"

    enabled: true

    # Notify section for all tasks in the chain
    notify:
      on-complete:
        message: "\"@channel: Action succeeded.\""
        routes:
          - "slack"

This is mostly useless because you want to control the message in each of the tasks. See section
below.

How do I setup different notifications for different tasks in the chain?
------------------------------------------------------------------------

The ``notify`` subsection is the same format as you have seen in examples above. You basically
place the subsection in action chain tasks. If you have a notify section for the action meta
and there is a notify section in the task, the task one will override. The relvant section of chain
action with task notify is shown below.

::

    -
      name: "make_reqmnts"
      ref: "core.remote"
      params:
        cmd: "cd {{repo_target}} && make requirements"
        hosts: "{{build_server}}"
        timeout: 300
      notify:
        on-failure:
          routes:
            - slack
          message: "Pytests failed on installing requirements."
      on-success: "make_lint"
    -
      name: "make_lint"
      ref: "core.remote"
      params:
        cmd: "cd {{repo_target}} && make .lint"  # .flake8 and .pylint
        hosts: "{{build_server}}"
        timeout: 180
      on-success: "make_tests"

How do I setup notifications for mistral?
-----------------------------------------

The method for global notifications for the workflow is the same as action chain. You have a notify
section in the action meta when registering. See an
`example <https://github.com/StackStorm/st2/blob/master/contrib/examples/actions/mistral-basic-two-tasks-with-notifications.yaml#L24>`_.
Unfortunately, notifications per task are not supported in mistral as a first class citizen yet.
This will be added in later releases.

How do I skip notifications for tasks in workflow or chain?
-----------------------------------------------------------

This is implemented as a runner parameter ``skip_notify``. If your chain or workflow contains
multiple tasks and you want some tasks to be "muted", you can do so by specifying skip_notify
and call out tasks in the action meta. For example,

::

    ---
    name: mistral-basic-two-tasks-with-notifications
    pack: examples
    description: Run mistral workflow with two tasks.
    runner_type: mistral-v2
    entry_point: workflows/mistral-basic-two-tasks-with-notifications.yaml
    enabled: true
    parameters:
      skip_notify:
        default:
          - "task2"
      context:
        default: {}
        immutable: true
        type: object
      task:
        default: null
        immutable: true
        type: string
      workflow:
        default: null
        immutable: true
        type: string
    notify:
      on-complete:
        message: "\"@channel: Action succeeded.\""
        routes:
          - "slack"

In the above example, notifications for "task2" will not be sent out. This feature is
particularly useful in combination with chatops where you want noisy tasks to not pollute
the chat client.

Chatops and notifications
-------------------------

If you enabled chatops, you get all the the things wired for you. You don't have to edit
action meta etc. You can still use ``skip_notify`` to skip notifications for certain tasks in a chain
or workflow. If you specified a notify section in meta or in tasks, those notification routes
will override chatops. Therefore, you might not see notifications in chat client.
See `issue <https://github.com/StackStorm/st2/issues/2018>`_ for example.
