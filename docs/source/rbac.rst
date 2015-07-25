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

System roles are roles which are available by default and can't be manipulated (manipulated and /
or deleted).

Currently, the following system roles are available:

* System administrator - Same as administrator, but this role is assigned to the first user in the
  system and can't be revoked.
* Administrator - All the permissions on all the resources.
* Observer - ``view`` permission on all the resources.

How it works
------------

TBW.

Defining roles and permission grants
------------------------------------

TBW.
