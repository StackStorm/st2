Mistral
=======
`Mistral <https://wiki.openstack.org/wiki/Mistral>`_ is an OpenStack project that manages and executes workflows as a service. Mistral is installed as a separate service named "mistral" along with |st2|. A Mistral workflow can be defined as a |st2| action in a Mistral workbook using the `v2 DSL <https://wiki.openstack.org/wiki/Mistral/DSLv2>`_. Both workbook and workflow definitions are supported. On action execution, |st2| writes the definition to Mistral and executes the workflow. Workflow can invoke other |st2| actions natively as subtasks. |st2| handles the translations and calls transparently in Mistral and actively polls Mistral for execution results.  |st2| actions in the workflow can be traced back to the original parent action that invoked the workflow.

Basic Workflow
++++++++++++++
Let's start with a very basic workflow that calls a |st2| action and notifies |st2| when the workflow is done. The files used in this example is also located under **/usr/share/doc/st2/examples** if |st2| is already installed. The first task is named **run-cmd** that executes a shell command on the local server where st2 is installed. A task can reference any registered |st2| action directly. In this example, the run-cmd task is calling **core.local** and passing the cmd as input. **core.local** is an action that comes installed with |st2|. When the workflow is invoked, |st2| will translate the workflow definition appropriately before sending it to Mistral. Let's save this as mistral-basic.yaml at **/opt/stackstorm/packs/examples/actions/workflows** where |st2| is installed.

.. literalinclude:: /../../contrib/examples/actions/workflows/mistral-basic.yaml

The following is the corresponding |st2| action metadata for example above. The |st2| pack for this workflow action is named "examples". Please note that the workflow is named fully qualified as "<pack>.<action>" in the definition above. The |st2| action runner is "mistral-v2". The entry point for the |st2| action refers to the YAML file of the workflow definition. Let's save this metadata as mistral-basic.json at /opt/stackstorm/packs/examples/actions/.

.. literalinclude:: /../../contrib/examples/actions/mistral-basic.json

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

Next, run ``st2 action create /opt/stackstorm/packs/examples/actions/mistral-basic.json`` to create this workflow action. This will register the workflow as examples.mistral-basic in |st2|. Then to execute the workflow, run ``st2 run examples.mistral-basic cmd=date -a`` where -a tells the command to return and not wait for the workflow to complete. If the workflow completed successfully, both the workflow **examples.mistral-basic** and the action **core.local** would have a **succeeded** status in the |st2| action execution list. By default, ``st2 execution list`` only returns top level executions. This means subtasks are not displayed.

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


Stitching a more Complex Workflow
+++++++++++++++++++++++++++++++++
The following is a mock up of a more complex workflow. In this mock up running simple printf and sleep commands, the workflow demonstrates nested workflows, fork, and join. 

.. literalinclude:: /../../contrib/examples/actions/workflows/mistral-workbook-complex.yaml

Since there are multiple workflows defined in this workbook, workflow author has to specify which workflow to execute in the metadata as shown in the workflow parameters below.

.. literalinclude:: /../../contrib/examples/actions/mistral-workbook-complex.json

To test out this workflow, save the metadata file to /opt/stackstorm/packs/examples/actions/ and the workflow file to /opt/stackstorm/packs/examples/actions/workflows. Run ``st2 action create /opt/stackstorm/packs/examples/actions/mistral-workbook-complex.json`` to create the action and run ``st2 run examples.mistral-workbook-complex vm_name="vmtest1" -a`` to test. 

More Examples
+++++++++++++++++++
There are more workflow examples under /usr/share/doc/st2/examples such as error handling, repeat, and retries. We will continue to share more of them at our github repos.
