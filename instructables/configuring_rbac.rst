Configuring RBAC
================

StackStorm enterprise edition brings support for Role Based Access Control(RBAC). RBAC allows a StackStorm administrator
control over what functions are accessible to a user within StackStorm.

**Possible scenarios :**

1. A user owns a pack i.e is able to view, create, delete, modify and where applicable execute various resources like
  actions, rules, sensors.
2. A user can create rules, execute actions and view a handful of actions.
3. A user capable of viewing actions in a pack but cannot execute any action.

This guide provides a walk-through of scenario 1 i.e configuring a user as a pack owner. The steps to be followed are by an
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

Once this user is created StackStorm will allow access to this user. (Optional) To validate try -

.. sourcecode:: bash

    $ st2 auth rbacu1 -p <RBACU1_PASSWORD>
    $ export ST2_AUTH_TOKEN=<USER_SCOPED_AUTH_TOKEN>
    $ st2 action list

Role creation
-------------
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
As a StackStorm administrator and on a box with StackStrom installed run -

.. sourcecode:: bash

    st2-apply-rbac-definitions

This command will sync up the StackStorm RBAC state with file system state. Only after running this command does
StackStorm know of the latest changes to RBAC permission grants.

Validation
----------
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

This walk-through showcases a narrow slice in StackStorm RBAC capabilities. For a more comprehensive refrence head
over to http://docs.stackstorm.com/latest/rbac.html.
