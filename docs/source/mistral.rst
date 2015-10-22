Mistral
=======
`Mistral <http://docs.openstack.org/developer/mistral/overview.html>`_ is an OpenStack project that manages and executes workflows as a service. Mistral is installed as a separate service named "mistral" along with |st2|. A Mistral workflow can be defined as a |st2| action in a Mistral workbook using the `v2 DSL <http://docs.openstack.org/developer/mistral/dsl/dsl_v2.html>`_. Both workbook and workflow definitions are supported. On action execution, |st2| writes the definition to Mistral and executes the workflow. Workflow can invoke other |st2| actions natively as subtasks. |st2| handles the translations and calls transparently in Mistral and actively polls Mistral for execution results.  |st2| actions in the workflow can be traced back to the original parent action that invoked the workflow.

Basic Workflow
++++++++++++++
Let's start with a very basic workflow that calls a |st2| action and notifies |st2| when the workflow is done. The files used in this example is also located under :github_st2:`/usr/share/doc/st2/examples </contrib/examples>` if |st2| is already installed (and you can :ref:`deploy examples <start-deploy-examples>`).
The first task is named **run-cmd** that executes a shell command on the local server where st2 is installed. A task can reference any registered |st2| action directly. In this example, the run-cmd task is calling **core.local** and passing the cmd as input. **core.local** is an action that comes installed with |st2|. When the workflow is invoked, |st2| will translate the workflow definition appropriately before sending it to Mistral. Let's save this as mistral-basic.yaml at **/opt/stackstorm/packs/examples/actions/workflows** where |st2| is installed.

.. literalinclude:: /../../contrib/examples/actions/workflows/mistral-basic.yaml

The following is the corresponding |st2| action metadata for example above. The |st2| pack for this workflow action is named "examples". Please note that the workflow is named fully qualified as "<pack>.<action>" in the definition above. The |st2| action runner is "mistral-v2". The entry point for the |st2| action refers to the YAML file of the workflow definition. Let's save this metadata as mistral-basic.yaml at /opt/stackstorm/packs/examples/actions/.

.. literalinclude:: /../../contrib/examples/actions/mistral-basic.yaml

The following table list optional parameters that can be defined in the workflow action. In the example, these optional parameters are set to immutable. It is good practice to set them to immutable even if they are empty since these are mistral specific parameters for workflow author.

+------------+--------------------------------------------------------+
| options    | description                                            |
+============+========================================================+
| workflow   | If definition is a workbook containing many workflows, |
|            | this specifics the main workflow to execute.           |
+------------+--------------------------------------------------------+
| task       | If the type of workflow is "reverse" , this specifies  |
|            | the task to invoke.                                    |
+------------+--------------------------------------------------------+
| context    | A dictionary containing additional workflow start up   |
|            | parameters.                                            |
+------------+--------------------------------------------------------+

Next, run ``st2 action create /opt/stackstorm/packs/examples/actions/mistral-basic.yaml`` to create this workflow action. This will register the workflow as examples.mistral-basic in |st2|. Then to execute the workflow, run ``st2 run examples.mistral-basic cmd=date -a`` where -a tells the command to return and not wait for the workflow to complete. If the workflow completed successfully, both the workflow **examples.mistral-basic** and the action **core.local** would have a **succeeded** status in the |st2| action execution list. By default, ``st2 execution list`` only returns top level executions. This means subtasks are not displayed.

+--------------------------+--------------+--------------+-----------+-----------------+---------------+
| id                       | action.ref   | context.user | status    | start_timestamp | end_timestamp |
+--------------------------+--------------+--------------+-----------+-----------------+---------------+
| 54ee54c61e2e24152b769a47 | examples     | stanley      | succeeded | Wed, 25 Feb     | Wed, 25 Feb   |
|                          | .mistral-    |              |           | 2015 23:03:34   | 2015 23:03:34 |
|                          | basic        |              |           | UTC             | UTC           |
+--------------------------+--------------+--------------+-----------+-----------------+---------------+

To display subtasks, run ``st2 execution get <execution-id> --tasks``.

+--------------------------+------------+--------------+-----------+------------------------------+------------------------------+
| id                       | action.ref | context.user | status    | start_timestamp              | end_timestamp                |
+--------------------------+------------+--------------+-----------+------------------------------+------------------------------+
| 54ee54c91e2e24152b769a49 | core.local | stanley      | succeeded | Wed, 25 Feb 2015 23:03:37    | Wed, 25 Feb 2015 23:03:37    |
|                          |            |              |           | UTC                          | UTC                          |
+--------------------------+------------+--------------+-----------+------------------------------+------------------------------+

Canceling Workflow Execution
++++++++++++++++++++++++++++
An execution of a Mistral workflow can be cancelled by running ``st2 execution cancel <execution-id>``. Workflow tasks that are still running will not be canceled and will run to completion. No new tasks for the workflow will be scheduled.

Publishing variables in mistral workflows
+++++++++++++++++++++++++++++++++++++++++

A mistral task can publish results from a task as variables that can be consumed in other tasks.

A simple examples is show below:

.. sourcecode:: YAML

    tasks:
        get_hostname:
            action: core.local
            input:
                cmd: "hostname"
            publish:
                hostname: <% $.get_hostname.stdout %>

In the above example, get_hostname is a core.local action which runs the command hostname.
core.local action produces an output consisting of fields ``stdout``, ``stderr``, ``exit_code`` etc.
We just want to publish the variable ``stdout`` from it so rest of tasks can consume.

Another example is shown below:

.. sourcecode:: YAML

    tasks:
        create_new_node:
            action: rackspace.create_vm
            input:
              name: <% $.hostname %>
              flavor_id: <% $.vm_size_id %>
              image_id: <% $.vm_image_id %>
              key_material: <% $.ssh_pub_key %>
              metadata:
                asg: <% $.asg %>
            publish:
              ipv4_address: '<% $.create_new_node.result.public_ips[1] %>'
              ipv6_address: '<% $.create_new_node.result.public_ips[0] %>'

In the above example, action rackspace.create_vm produces a results object. We just want to publish
the IP addresses from ``public_ips`` list field in results object.

Such published variables are accessible as input parameters to other tasks in the workflow. An
example of using ``ipv4_address`` from the above example in another task is shown below:

.. sourcecode:: YAML

    tasks:
        # ... <snap>

        setup_ipv4_dns:
            action: rackspace.create_dns_record
            wait-before: 1 # delay, in seconds
            input:
              name: '<% $.hostname %>.<% $.asg %>.<% $.domain %>'
              zone_id: <% $.dns_zone_id %>
              type: 'A'
              data: <% $.ipv4_address %>

        # .... </snap>

Stitching a more Complex Workflow
+++++++++++++++++++++++++++++++++
The following is a mock up of a more complex workflow. In this mock up running simple printf and sleep commands, the workflow demonstrates nested workflows, fork, and join.

.. literalinclude:: /../../contrib/examples/actions/workflows/mistral-workbook-complex.yaml

Since there are multiple workflows defined in this workbook, workflow author has to specify which workflow to execute in the metadata as shown in the workflow parameters below.

.. literalinclude:: /../../contrib/examples/actions/mistral-workbook-complex.yaml

To test out this workflow, save the metadata file to /opt/stackstorm/packs/examples/actions/ and the workflow file to /opt/stackstorm/packs/examples/actions/workflows. Run ``st2 action create /opt/stackstorm/packs/examples/actions/mistral-workbook-complex.yaml`` to create the action and run ``st2 run examples.mistral-workbook-complex vm_name="vmtest1" -a`` to test.

More Examples
+++++++++++++++++++
There are more workflow examples under :github_st2:`/usr/share/doc/st2/examples </contrib/examples/actions/workflows/>` such as error handling, repeat, and retries.

Check out this step-by-step tutorial on building a workflow in |st2| http://stackstorm.com/2015/07/08/automating-with-mistral-workflow/

More details about Mistral can be found at http://docs.openstack.org/developer/mistral/.
