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

Role
~~~~

Role contains a set of permissions (permission grants) which apply to the resources. Permission
grants are usually grouped together in a role using a specific criteria (e.g. by project, location,
team, etc).

Roles are assigned to the users. Each user can have multiple roles assigned to it.

Permission grant
~~~~~~~~~~~~~~~~

Permission grant grants a particular permission (permission type) to a particular resource. For
example, you could grant an execute permission (``ACTION_EXECUTE``) to an action ``core.local``.

The table below contains a list of all the available permission types.

.. include:: _includes/available_permission_types.rst

System roles
------------

System roles are roles which are available by default and can't be manipulated (modified and /
or deleted).

Currently, the following system roles are available:

* System administrator - Same as administrator, but this role is assigned to the first user in the
  system and can't be revoked.
* Administrator - All the permissions on all the resources.
* Observer - ``view`` permission on all the resources.

How it works
------------

User permissions are checked when a user performs an API request. If user has the necessary
permissions the API operation proceeds normally, otherwise access denied error is returned and
the error is logged in the audit log.

Permission inheritance
~~~~~~~~~~~~~~~~~~~~~~

By default all the pack resources inherit all the permission from a pack. This means that if you
grant "execute" permission to a pack, user will be able to execute all the actions inside that
pack. Similarly, if you grant "delete" permission to a pack, user will be able to delete all the
resources in a pack (action, rule).

Defining roles and permission grants
------------------------------------

Roles and permission grants are defined in YAML files which are located in on a file system in the
following directory: ``/opt/stackstorm/rbac/``.

TBD - File names and format + examples.

Maybe?

- rbac/<role_name>_role.yaml
- rbac/<username>_grants.yaml

Synchronizing RBAC information in the database with the one from disk
---------------------------------------------------------------------

As described above, RBAC definitions are defined in YAML files located in the
``/opt/stackstorm/rbac/`` directory. For those definitions to take an effect,
you need to apply them using ``st2-apply-rbac-definitions``.

Usually you will want to run this script every time you want the RBAC
definitions you have written to take an effect.

- note on infra as a code approach
- those files can and should be version controlled 
- only ppl who have access to git can write them

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
