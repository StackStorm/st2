Known security issues and limitations
=====================================

This page describes known security issues and limitations and information on how
to avoid, or when not possible, mitigate them.

General
-------

User with access to core.local action can read stanley user private SSH keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default ``core.local`` action runs under StackStorm system user
(``stanley``) which also has paswordless sudo access enabled. The same user is
also used to execute ``core.remote`` actions on the remote systems. For that to
work, `~/.ssh` directory of this user needs to contain private key which is
used to access the remote systems. This means that every user which has access
to the ``core.local`` action can read this private key.

**Mitigation**

To mitigate this issue you should only grant ``action_execute`` permission on
``core.local`` and ``core.local_sudo`` action to the trustworthy users (or even
better, stick with the default and only allow this action to be executed by
administrators).

If you don't need ``core.local_sudo`` action and / or you only want
``core.local`` actions to be executed as the default system user you can also
disable sudo access for this user. In default installation this means removing
``/etc/sudoers.d/st2`` file.

RBAC
----

Action execute permission escalation via workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Right now if the user doesn't have ``action_execute`` permission on a
particular action, but they have ``action_create`` permission, they can
circumvent the lack of execute permissions by creating a new workflow action
which uses an action they don't have the execute permission to.

**Mitigation**

To mitigate this issue you should only grant ``action_create`` permission to
the trustworthy users and users which really need it.

Mistral
-------

Potentially sensitive information can leak into the Mistral logs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Right now Mistral doesn't support marking specific workflow arguments and result
objects as secrets. This means if you pass a parameter which contains a secret
or sensitive information to Mistral, the value of this parameter might end up
in the Mistral log file.

**Mitigation**

To mitigate this issue you should disable Mistral workflow trace log. In a
default installation you can do that by replacing the following file
``/etc/mistral/wf_trace_logging.conf`` with an empty one.
