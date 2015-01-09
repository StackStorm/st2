Mistral
=======
`Mistral <https://wiki.openstack.org/wiki/Mistral>`_ is an OpenStack project that manages and executes workflows as a service. Mistral is installed as a separate service named "mistral" along with |st2|. A Mistral workflow can be defined as an |st2| action in a Mistral workbook using the `DSL v2 <https://wiki.openstack.org/wiki/Mistral/DSLv2>`_. On action execution, |st2| writes the workbook to Mistral and executes the workflow in the workbook. The workflow can invoke other |st2| actions as subtasks. There're custom actions in Mistral responsible for handling calls and context for |st2|. Subtasks in the workflow that are |st2| actions are tracked under the parent workflow in |st2|. |st2| actively polls Mistral for execution results.

Basic Workflow
++++++++++++++
Let's start with a very basic workflow that calls a |st2| action and notifies |st2| when the workflow is done. The files used in this example is also located under /usr/share/doc/st2/examples if |st2| is already installed. The first task is named **run-cmd** that executes a shell command on the local server where st2 is installed. The run-cmd task is calling **core.local** and passing the cmd as input. **core.local** is an action that comes installed with |st2|. In the workflow, we can reference |st2| action directly. When the workflow is invoked, |st2| will translate the workflow definition appropriately before sending it to Mistral. Let's save this as mistral-basic.yaml at /opt/stackstorm/packs/examples/actions/ where |st2| is installed.

.. literalinclude:: /../../contrib/examples/actions/mistral-basic.yaml

The following is the corresponding |st2| action metadata for example above. The |st2| pack for this workflow action is named "examples". Please note that the workbook is named fully qualified as "<pack>.<action>" in the workbook definition above. The |st2| action runner is "mistral-v2". The entry point for the |st2| action refers to the YAML file of the workbook definition. Under the parameters section, we added an immutable parameter that specifies which workflow in the workbook to execute and a second parameter that takes the command to execute. Let's save this metadata as mistral-basic.json at /opt/stackstorm/packs/examples/actions/.

.. literalinclude:: /../../contrib/examples/actions/mistral-basic.json

Next, run the following |st2| command to create this workflow action. This will register the workflow as examples.mistral-basic in |st2|. ::

    st2 action create /opt/stackstorm/packs/examples/actions/mistral-basic.json


To execute the workflow, run the following command where -a tells the command to return and not wait for the workflow to complete. ::

    st2 run examples.mistral-basic cmd=date -a

If the workflow completed successfully, both the workflow **examples.mistral-basic** and the action **core.local** would have a **succeeded** status in the |st2| action execution list. ::

    +--------------------------+------------------------+--------------+-----------+-----------------------------+
    | id                       | action                 | context.user | status    | start_timestamp             |
    +--------------------------+------------------------+--------------+-----------+-----------------------------+
    | 545169bf9c99383e585e2934 | examples.mistral-basic |              | succeeded | 2014-11-03T10:00:11.808000Z |
    | 545169c09c99383e585e2935 | core.local             |              | succeeded | 2014-11-03T10:00:12.084000Z |
    +--------------------------+------------------------+--------------+-----------+-----------------------------+

Stitching a more Complex Workflow
+++++++++++++++++++++++++++++++++
Let's say we need to upgrade and reboot all the members of a MongoDB replica set in production. In this mockup, the workflow orchestrates a rolling upgrade. A member node is upgraded first and then becomes the primary before upgrading the remaining nodes of the replica set. Part of this example here references the MongoDB `tutorial <http://docs.mongodb.org/manual/tutorial/force-member-to-be-primary/>`_ on forcing a member to be a primary in a replica set. The workflow takes two input arguments: primary server and the member servers. Then the workflow executes the following tasks.

#. Checks the status of the replica set.
#. Select a new primary from the list of members and outputs the candidate and the other secondary.
#. Upgrade the candidate node.
#. Freeze the secondary node for x seconds. During this duration, the secondary node will not attempt to become the primary.
#. Step down the current primary node for x seconds so it is not eligible.
#. Wait for the candidate node to become primary.
#. Upgrade the remaining nodes.

::

    name: 'mongdb.rolling-upgrade'
    version: '2.0'
    workflows:
        main:
            type: direct
            input:
                - primary
                - members
                - duration
            tasks:
                replica-set-check-status:
                    action: mongodb.rs-check-status primary={$.primary}
                    on-success:
                        - elect-primary
                elect-primary:
                    action: mongodb.elect-primary members={$.members}
                    publish:
                        candidate: $.candidate
                        secondary: $.secondary
                    on-success:
                        - update-candidate
                update-candidate:
                    action: mongodb.run-update-xyz node={$.candidate}
                    on-success:
                        - freeze-secondary
                freeze-secondary:
                    action: mongodb.freeze node={$.secondary} duration={$.duration}
                    on-success:
                        - step-down-primary
                step-down-primary:
                    action: mongodb.step-down primary={$.primary} duration={$.duration}
                    policies:
                        wait-after: $.duration
                    on-success:
                        - update-primary
                update-primary:
                    action: mongodb.run-update-xyz node={$.primary}
                    on-success:
                        - update-secondary
                update-secondary:
                    action: mongodb.run-update-xyz node={$.secondary}
