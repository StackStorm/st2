Configuring RBAC
================

StackStorm enterprise edition brings support for Role Based Access Control(RBAC). RBAC allows a StackStorm administrator
control over what functions are accessible to a user within StackStorm.

Possible scenarios :

- A user owns a pack i.e is able to view, create, delete, modify and where applicable execute various resources like
  actions, rules, sensors.
- A user can create rules, execute actions and view a handful of actions.
- A user capable of viewing actions in a pack but cannot execute any action.

This guide provides a walk-through on how to configure a user as a pack owner. The steps to be followed are by an
Administrator of StackStorm on a box that is running StackStorm.

User creation
-------------
All user and password management is kept outside of StackStorm. Documentation on Authentication_ describe how to
confirgure StackStorm with various identity providers.

.. _Authentication: http://docs.stackstorm.com/latest/config/authentication.html

For sake of this guide let us assume that the identify provider is managed by the OS on which StackStorm runs.

To create a user and set-up a password on most linux systems -

.. sourcecode:: bash

    $ useradd rbacu1

    $ passwd rbacu1

Once this user is created StackStorm will allow access to this user. Optionally, to validate try -

.. sourcecode:: bash

    $ st2 auth rbacu1 -p <RBACU1_PASSWORD>
    $ export ST2_AUTH_TOKEN=<USER_SCOPED_AUTH_TOKEN>
    $ st2 action list

Role creation
-------------
A newly created user has no permissions assigned. Each permission must be explicitly assign to a user. To assign a
permission grants StackStorm requires creation of a role. In this case we are trying to create a pack owner role.

Create file `/opt/stackstorm/rbac/roles/x_pack_owner.yaml` with the following content -

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

In this case for a `pack owner` role would require the user to be able to view, create, modify and delete all contents
of a pack. In this particular case we are choosing pack `x` as the target of ownership.

See http://docs.stackstorm.com/latest/rbac.html#available-permission-types for a full list of permission types.

Role assignment
---------------
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
-------------
Once again as a StackStorm administrator and on a box with StackStrom installed run -

.. sourcecode:: bash

    st2-apply-rbac-definitions

This command will sync up the contents of StackStorm with content of the file system. Only after running this command does
StackStorm know of the latest changes to RBAC permission grants.

Validation
----------
XXX
