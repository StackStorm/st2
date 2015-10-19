Role Based Access Control
=========================

.. note::

   Role Based Access Control (RBAC) is only available in StackStorm enterprise edition. For more
   information about enterprise edition and differences between community and enterprise edition,
   please see this page - https://stackstorm.com/product/#enterprise.

|st2| implements Role Based Access (abbreviated RBAC) control which allows system administrators
and operators to restrict users access and limit the operations they can perform.
For instance, you could give your database operator access only to the database related actions.

Go over detailed overview below, or jump straight to an :ref:`example of usage <rbac-using_rbac>`.

Terminology
-----------

This section describes basic concepts with which you need to be familiar to understand and
efficiently utilize the RBAC system.

User
~~~~

A user represents an entity (person / robot) which needs to be authenticated and interacts with
|st2| through the API.

User permissions are represented as a union of permission grants which are assigned to all the user
roles.

By default when a new StackStorm user is created, this user has no roles assigned to it, meaning it
doesn't have access to perform any API operation which is behind the RBAC wall.

Role
~~~~

Role contains a set of permissions (permission grants) which apply to the resources. Permission
grants are usually grouped together in a role using a specific criteria (e.g. by project, location,
team, responsibility, etc.).

Roles are assigned to the users. Each user can have multiple roles assigned to it and each role can
be assigned to multiple users.

System roles
------------

System roles are roles which are available by default and can't be manipulated (modified and / or
deleted).

Currently, the following system roles are available:

* **System administrator** - Same as administrator, but this role is assigned to the first user in the
  system and can't be revoked.
* **Administrator** - All the permissions on all the resources.
* **Observer** - ``view`` permission on all the resources.

Permission grant
~~~~~~~~~~~~~~~~

Permission grant grants a particular permission (permission type) to a particular resource. For
example, you could grant an execute / run permission (``action_execute``) to an action
``core.local``.

In general, there are five permission types available for each supported resource type:

* ``view`` - Ability to view a specific resource or ability to list all the
  resources of a specific type.
* ``create`` - Ability to create a new resource.
* ``modify`` - Ability to modify (update) an existing resource.
* ``delete`` - Ability to delete a specific resource.
* ``all`` - Ability to perform all the supported operations on a specific resource. For example,
  if you grant ``action_all`` on a particular action this implies the following permissions:
  ``action_view``, ``action_create``, ``action_modify``, ``action_delete`` and ``action_execute``.

In addition to that, there is also a special ``execute`` (``action_execute``) permission type
available for actions. This permission allows users to execute (run) a particular action.

Keep in mind that in StackStorm workflow is just an action so if you want someone to be able to
execute a particular workflow, you simply need to grant them ``action_execute`` permission on that
workflow.

As described in the table below, ``create``, ``modify``, ``delete`` and ``execute`` permissions
also implicitly grant corresponding ``view`` permission. This means that, for example, if you
grant ``action_execute`` permission on a particular action, user will also be able to view and
retrieve details for this particular action.

.. _ref-rbac-available-permission-types:

Available permission types
~~~~~~~~~~~~~~~~~~~~~~~~~~

The table below contains a list of all the available permission types.

.. include:: _includes/available_permission_types.rst

This list can also be retrieved using the RBAC meta API (``GET /v1.0/rbac/permission_types``).

User permissions
~~~~~~~~~~~~~~~~

User permissions (also called effective user permission set) are represented as a union of all
the permission grants which are assigned to the user roles.

For example, if user has the following two roles assigned to it:

.. literalinclude:: ../../st2tests/st2tests/fixtures/rbac/roles/role_five.yaml
    :language: yaml

.. literalinclude:: ../../st2tests/st2tests/fixtures/rbac/roles/role_six.yaml
    :language: yaml

The effective user permission set which is used during RBAC checks is:

* ``action_execute`` on ``action:dummy_pack_1:my_action_1``
* ``action_execute`` on ``action:dummy_pack_1:my_action_2``

RBAC system uses a whitelist approach which means there is no possibility of a conflicting and
contradictory permission grants in different roles (e.g. one role would grant a particular
permission and other role would revoke it).

Resource
~~~~~~~~

In the context of RBAC, resource refers to the resource to which the permission grant applies to.
Currently permission grants can be applied to the following resource types:

* packs
* sensors
* actions
* rules
* executions
* webhooks

Resource is identified by and you refer to it in the permission grants using ``uid``. UID is a
identifier which is unique for each resource in the StackStorm installation. UIDs follow this
format: ``<resource type>:<resourc specific identifier value>`` (e.g. ``pack:libcloud``,
``action:libcloud:list_vms``, etc.).

You can retrieve UID of a particular resource by listing all the resources of a particular type or
by retrieving details of a single resource using either an API or CLI.

For example:

.. sourcecode:: bash

    st2 action list
    +-------------------------+-------------------------+-----------+-------------------------+-------------------------+
    | uid                     | ref                     | pack      | name                    | description             |
    +-------------------------+-------------------------+-----------+-------------------------+-------------------------+
    | action:core:remote      | core.remote             | core      | remote                  | Action to execute       |
    |                         |                         |           |                         | arbitrary linux command |
    |                         |                         |           |                         | remotely.               |
    +-------------------------+-------------------------+-----------+-------------------------+-------------------------+

How it works
------------

User permissions are checked when a user performs an operation using the API. If user has the
necessary permissions* the API operation proceeds normally, otherwise access denied error is
returned and the error is logged in the audit log.

Permission inheritance
~~~~~~~~~~~~~~~~~~~~~~

**Pack resources**

Pack resources inherit all the permission from a pack. This means that if you grant
``action_execute`` permission to a pack, user will be able to execute all the actions inside that
pack. Similarly, if you grant ``rule_create`` permission to a pack, user will be able to create new
rules in that pack.

**Executions**

Executions inherit permissions from the action they belong and from the action's parent pack. This
means that if you grant ``action_view`` permission on a particular action, the user will be able to
view all the executions which belong to that action. Similarly, if you grant ``action_view`` to a
parent pack of the action execution belongs to, user will be able to view all the executions which
belong to the action with that parent pack.

On top of that, granting ``action_execute`` on a particular pack or action also grants
``execution_rerun`` and ``execution_stop`` to all the executions which belong to that action.

Defining roles and assignments
------------------------------

To follow infrastructure as code approach, roles and user role assignments are defined in YAML
files which are stored on a filesystem in the following directory: ``/opt/stackstorm/rbac/``.

Those definitions being simple YAML files means you can (and should) version control and manage
them in the same way you version control and manage other source code and infrastructure artifacts.

Both, roles and user role assignments are loaded in lexicographical order based on the filename.
For example, if you have two role definitions in the files named ``role_b.yaml`` and
``role_a.yaml``, ``role_a.yaml`` will be loaded before ``role_b.yaml``.

Defining roles and permission grants
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Roles and permission grants are defined in YAML files which are located on a filesystem in the
following directory: ``/opt/stackstorm/rbac/roles/``. Each file defines role information and
associated permission grants for a single role which means that if you want to define **n** roles
you will need **n** files.

Example role definition (``/opt/stackstorm/rbac/roles/role_sample.yaml``) is shown below:

.. literalinclude:: ../../st2tests/st2tests/fixtures/rbac/roles/role_sample.yaml
    :language: yaml

The example above contains a variety of permission grants with the corresponding explanation
(comments).

Defining user role assignments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

User role assignments are defined in YAML files which are located on a filesystem in the following
directory: ``/opt/stackstorm/rbac/assignments/``. Each file defines assignments for a single user
which means that if you want to define assignments for **n** users, you will need **n** files.

Example role definition (``/opt/stackstorm/rbac/assignments/user4.yaml``) is shown below:

.. literalinclude:: ../../st2tests/st2tests/fixtures/rbac/assignments/user4.yaml
    :language: yaml

In the example above we assign user with the username ``user4`` two roles -
``role_one`` (a custom role which needs to be defined as described above) and
``observer`` (system role).

Applying RBAC definitions
-------------------------

As described above, RBAC definitions are defined in YAML files located in the
``/opt/stackstorm/rbac/`` directory. For those definitions to take an effect,
you need to apply them using ``st2-apply-rbac-definitions`` script.

Usually you will want to run this script every time you want the RBAC
definitions you have written to take an effect.

For example:

.. code-block:: bash

    st2-apply-rbac-definitions

    2015-08-12 22:30:18,439 - INFO - Synchronizing roles...
    2015-08-12 22:30:18,441 - DEBUG - New roles: set([])
    2015-08-12 22:30:18,442 - DEBUG - Updated roles: set(['role_two', 'role_one', 'role_three'])
    2015-08-12 22:30:18,442 - DEBUG - Removed roles: set([])
    2015-08-12 22:30:18,443 - DEBUG - Deleting 3 stale roles
    2015-08-12 22:30:18,444 - DEBUG - Deleted 3 stale roles
    2015-08-12 22:30:18,446 - DEBUG - Deleting 5 stale permission grants
    2015-08-12 22:30:18,447 - DEBUG - Deleted 5 stale permission grants
    2015-08-12 22:30:18,448 - DEBUG - Creating 3 new roles
    2015-08-12 22:30:18,454 - DEBUG - Created 3 new roles
    2015-08-12 22:30:18,458 - INFO - Synchronizing users role assignments...
    2015-08-12 22:30:18,460 - DEBUG - New assignments for user "user1": set([])
    2015-08-12 22:30:18,461 - DEBUG - Updated assignments for user "user1": set(['role_two', 'role_one'])
    2015-08-12 22:30:18,461 - DEBUG - Removed assignments for user "user1": set([])
    2015-08-12 22:30:18,462 - DEBUG - Removed 2 assignments for user "user1"
    2015-08-12 22:30:18,464 - DEBUG - Created 2 new assignments for user "user1"

.. _rbac-using_rbac:

Using RBAC - example
--------------------

**Possible scenarios :**

1. A user owns a pack i.e is able to view, create, delete, modify and where applicable execute various resources like actions, rules, sensors.
2. A user can create rules, execute actions and view a handful of actions.
3. A user capable of viewing actions in a pack but cannot execute any action.

This example provides a walk-through of scenario 1 i.e configuring a user as a pack owner. The steps to be followed are by an
Administrator of StackStorm on a box that is running StackStorm.

User creation
~~~~~~~~~~~~~
All user and password management is kept outside of StackStorm. Documentation on :doc:`authentication <authentication>` describes how to confirgure StackStorm with various identity providers.

For sake of this example let us assume that the identify provider is managed by the OS on which StackStorm runs.

To create a user and set-up a password on most linux systems -

.. sourcecode:: bash

    $ useradd rbacu1
    $ passwd rbacu1

Once this user is created StackStorm will allow access to this user. (Optional) To validate try -

.. sourcecode:: bash

    $ st2 auth rbacu1 -p <RBACU1_PASSWORD>
    $ export ST2_AUTH_TOKEN=<USER_SCOPED_AUTH_TOKEN>
    $ st2 action list

Role creation
~~~~~~~~~~~~~
A newly created user has no assigned permissions. Each permission must be explicitly assigned to a user. To assign
permission grants StackStorm requires creation of a role and then associating this role with a user. In this case we are trying to create a pack owner role.

Lets first make sure there is a pack `x` we can use to experiment.

.. sourcecode:: bash

    $ cd /opt/stackstorm/packs/
    $ mkdir x
    $ mkdir x/actions x/rules x/sensors
    $ touch pack.yaml
    $ touch config.yaml
    $ touch requirements.txt
    $ cp core/icon.png x/icon.png

Now we setup a role. Create file `/opt/stackstorm/rbac/roles/x_pack_owner.yaml` with the following content -

.. sourcecode:: bash

    ---
    name: "x_pack_owner"
    description: "Owner of pack x"
    enabled: true
    permission_grants:
        -
            resource_uid: "pack:x"
            permission_types:
               - "pack_all"
               - "sensor_all"
               - "rule_all"
               - "action_all"

A `pack owner` role would require the user to be able to view, create, modify and delete all contents
of a pack. Again, lets pick pack `x` as the target of ownership.

See :ref:`available permission types<ref-rbac-available-permission-types>` for a full list of permission types.

Role assignment
~~~~~~~~~~~~~~~
Creation of a role is followed by assignment of a role to the user. Create file `/opt/stackstorm/rbac/assignments/rbacu1.yaml`
with the following content -


.. sourcecode:: bash

    ---
    username: "rbacu1"
    description: "rbacu1 assignments"
    enabled: true
    roles:
        - "x_pack_owner"

Applying RBAC
~~~~~~~~~~~~~
As a StackStorm administrator and on a box with StackStrom installed run -

.. sourcecode:: bash

    st2-apply-rbac-definitions

This command will sync up the StackStorm RBAC state with file system state. Only after running this command does
StackStorm know of the latest changes to RBAC permission grants.

Validation
~~~~~~~~~~
Lets take what we have achieved for a spin using the StackStorm CLI.

1. Setup Authentication token.

.. sourcecode:: bash

    $ st2 auth rbacu1 -p <RBACU1_PASSWORD>
    $ export ST2_AUTH_TOKEN=<USER_SCOPED_AUTH_TOKEN>
    $ st2 action list

2. Validate rule visibility and creation.

.. sourcecode:: bash

    $ cd /opt/stackstorm/packs/x
    $ cp /usr/share/doc/st2/examples/rules/sample_rule_with_timer.yaml rules/
    $ sed -i 's/pack: "examples"/pack: "x"/g' rules/sample_rule_with_timer.yaml
    $ st2 rule create rules/sample_rule_with_timer.yaml
    $ st2 rule get x.sample_rule_with_timer.yaml
    $ st2 rule delete x.sample_rule_with_timer.yaml

    # Expect Failure
    $ st2 rule get <EXISTING_RULE_REF>

3. Validation action visibility, creation and execute.

.. sourcecode:: bash

    $ cd /opt/stackstorm/packs/x
    $ cp /usr/share/doc/st2/examples/actions/local.yaml actions/
    $ echo "pack: x" >> actions/local.yaml
    $ st2 action create actions/local.yaml
    $ st2 action get x.local-notify
    $ st2 run x.local-notify hostname
    $ st2 action delete x.local-notify

    # Expect failure
    $ st2 action get core.local
    $ st2 run core.local hostname
