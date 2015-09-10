Role Based Access Control
=========================

|st2| implements Role Based Access (abbreviated RBAC) control which allows system administrators
and operators to restrict users access and limit the operations they can perform.

For example, you could give your database operator access only to the database related actions.

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
``execution_re_run`` and ``execution_stop`` to all the executions which belong to that action.

Defining roles and user role assignments
----------------------------------------

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

Example role definition (``/opt/stackstorm/rbac/roles/role_four.yaml``) is shown below:

.. literalinclude:: ../../st2tests/st2tests/fixtures/rbac/roles/role_four.yaml
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

Synchronizing RBAC information in the database with the one from disk
---------------------------------------------------------------------

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
