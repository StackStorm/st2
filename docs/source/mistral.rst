Mistral
=======
`Mistral <https://wiki.openstack.org/wiki/Mistral>`_ is an OpenStack project that manages and executes workflows as a service. Mistral is installed as a separate service named "mistral" along with |st2|. A Mistral workflow can be defined as an |st2| action in a Mistral workbook using the `DSL v2 <https://wiki.openstack.org/wiki/Mistral/DSLv2>`_. On action execution, |st2| writes the workbook to Mistral and executes the workflow in the workbook. The workflow can invoke other |st2| actions as subtasks. There're custom actions in Mistral responsible for handling calls and context for |st2|. Subtasks in the workflow that are |st2| actions are tracked under the parent workflow in |st2|. On completion of the workflow, Mistral will communicate the status of the workflow execution back to |st2|.

Custom Mistral Actions
++++++++++++++++++++++
StackStorm introduces two custom actions in Mistral: **st2.action** and **st2.callback**. These custom actions are used for a unit of work or subtask in a workflow. **st2.action** should be used to schedule a st2 action and **st2.callback** should be used to update the status of the parent action execution in |st2| on workflow completion in Mistral.

Basic Workflow
++++++++++++++
Let's start with a very basic workflow that calls a |st2| action and notifies |st2| when the workflow is done. The files used in this example is also located under /usr/share/doc/st2/examples if |st2| is already installed. The first task is named **http-get** that does a HTTP GET on the given URL. A st2.action takes two input arguments: ref (or name) of the |st2| action and a list of input parameters for the |st2| action. In this case, the http-get task is calling **core.http** and passing the URL as input. On success, the task **callback-on-success** returns the body of the HTTP response to |st2|. On error, the task **callback-on-error** notifies |st2| an error has occurred. Let's save this as mistral-basic.yaml at /opt/stackstorm/examples/actions where |st2| is installed.

.. literalinclude:: /../../contrib/examples/actions/mistral-basic.yaml

The following is the corresponding |st2| action metadata for example above. The |st2| pack for this workflow action is named "examples". Please note that the workbook is named fully qualified as "<pack>.<action>" in the workbook definition above. The |st2| action runner is "mistral-v2". The entry point for the |st2| action refers to the YAML file of the workbook definition. Under the parameters section, we added an immutable parameter that specifies which workflow in the workbook to execute and a second parameter that takes the URL to GET. Let's save this metadata as mistral-basic.json at /opt/stackstorm/examples/actions.

.. literalinclude:: /../../contrib/examples/actions/mistral-basic.json

Next, run the following |st2| command to create this workflow action. This will register the workflow as examples.mistral-basic in |st2|. ::

    st2 action create /opt/stackstorm/examples/actions/mistral-basic.json

To execute the workflow, run the following command where -a tells the command to return and not wait for the workflow to complete. ::

    st2 run examples.mistral-basic url=http://www.google.com -a

If the workflow completed successfully, both the workflow **examples.mistral-basic** and the action **core.http** would have a **succeeded** status in the |st2| action execution list. ::

    +--------------------------+------------------------+--------------+-----------+-----------------------------+
    | id                       | action                 | context.user | status    | start_timestamp             |
    +--------------------------+------------------------+--------------+-----------+-----------------------------+
    | 545169bf9c99383e585e2934 | examples.mistral-basic |              | succeeded | 2014-11-03T10:00:11.808000Z |
    | 545169c09c99383e585e2935 | core.http              |              | succeeded | 2014-11-03T10:00:12.084000Z |
    +--------------------------+------------------------+--------------+-----------+-----------------------------+

Stitching a more Complex Workflow
+++++++++++++++++++++++++++++++++
Let's say we need to upgrade and reboot all the members of a MongoDB replica set in production. In this mockup, the workflow orchestrates a rolling upgrade. A member node is upgraded first and then becomes the primary before upgrading the remaining nodes of the replica set. Part of this example here references the MongoDB `tutorial <http://docs.mongodb.org/manual/tutorial/force-member-to-be-primary/>`_ on forcing a member to be a primary in a replica set. The workflow takes two input arguments: primary server and the member servers. Then the workflow executes the following tasks. If on any error, the workflow runs the task **callback-on-error** and exit.

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
                    action: st2.action
                    input:
                        ref: mongodb.rs-check-status
                        parameters:
                            primary: $.primary
                    on-error:
                        - callback-on-error
                    on-success:
                        - elect-primary
                elect-primary:
                    action: st2.action
                    input:
                        ref: mongodb.elect-primary
                        parameters:
                            members: $.members
                    publish:
                        candidate: $.candidate
                        secondary: $.secondary
                    on-error:
                        - callback-on-error
                    on-success:
                        - update-candidate
                update-candidate:
                    action: st2.action
                    input:
                        ref: mongodb.run-update-xyz
                        parameters:
                            node: $.candidate
                    on-error:
                        - callback-on-error
                    on-success:
                        - freeze-secondary
                freeze-secondary:
                    action: st2.action
                    input:
                        ref: mongodb.freeze
                        parameters:
                            node: $.secondary
                            duration: $.duration
                    on-error:
                        - callback-on-error
                    on-success:
                        - step-down-primary
                step-down-primary:
                    action: st2.action
                    input:
                        ref: mongodb.step-down
                        parameters:
                            primary: $.primary
                            duration: $.duration
                    policies:
                        wait-after: $.duration
                    on-error:
                        - callback-on-error
                    on-success:
                        - update-primary
                update-primary:
                    action: st2.action
                    input:
                        ref: mongodb.run-update-xyz
                        parameters:
                            node: $.primary
                    on-error:
                        - callback-on-error
                    on-success:
                        - update-secondary
                update-secondary:
                    action: st2.action
                    input:
                        ref: mongodb.run-update-xyz
                        parameters:
                            node: $.secondary
                    on-error:
                        - callback-on-error
                    on-success:
                        - callback-on-success
                callback-on-error:
                    action: st2.callback
                    input:
                        state: "ERROR"
                        result: "Unexpected failure."
                callback-on-success:
                    action: st2.callback
                    input:
                        state: "SUCCESS"
                        result: "Replica set upgraded. Promoted {$.candidate} to primary."

