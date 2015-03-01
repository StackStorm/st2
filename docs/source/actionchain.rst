ActionChain
============

ActionChain is a no-frills linear workflow. On completion of a constituent action the choice between on-success and on-failure is evaluated to pick the next action. This implementation allows for passing of data between actions and finally publishes the result of each of the constituent action elements. From perspective of |st2| an ActionChain is itself an action therefore all the features of an action like execution from cli, usage in Rules etc. are automatically supported.

Authoring an ActionChain
------------------------

ActionChain's are described in YAML (JSON supported for backward compatibiltiy) and placed inside a pack similar to other script or python actions. An ActionChain must also be associated with a metadata file that allows it to be registered as an Action by |st2|. This metadata contains name and parameter description of an action.


ActionChain definition
~~~~~~~~~~~~~~~~~~~~~~

Following is sample ActionChain workflow definition named :github_st2:`echochain.yaml
<contrib/examples/actions/chains/echochain.yaml>`:

.. literalinclude:: /../../contrib/examples/actions/chains/echochain.yaml
   :language: yaml

Details:

* `chain` is the array property that contains action elements.
* Action elements are named action execution specifications. The name is scoped to an ActionChain and is used as a reference to an action element.
* `ref` property of an action element points to an Action registered in |st2|.
* `on-success` is the link to action element to invoke next on a successful execution. If not provided the ActionChain will terminate with status set to success.
* `on-failure` is the link to action element to invoke next on a failed execution. If not provided the ActionChain will terminate with the status set to error.
* `default` is an optional top level property that specifies the start of an ActionChain.

ActionChain metadata
~~~~~~~~~~~~~~~~~~~~

ActionChain action defined and operated like :doc:`any other action <actions>`.
The action medatata schema
is the same for any action in the system: specify ``action-chain`` as a runner,
and point to the workflow definition file
in the ``entry_point``. The action definition metadata :github_st2:`echochain.meta.yaml
<contrib/examples/actions/echochain.meta.yaml>` for an ActionChain :github_st2:`echochain.yaml
<contrib/examples/actions/chains/echochain.yaml>` looks like this:

.. literalinclude:: /../../contrib/examples/actions/echochain.meta.yaml
   :language: yaml


Once action definition and metadata files are created, load the action:

.. code-block:: bash

    # Register the action
    st2 action create /opt/stackstorm/packs/default/actions/echochain.meta.yaml
    # Check it is available
    st2 action list --pack=default
    # Run it
    st2 run default.echochain

Any changes in ActionChain workflow definition are picked up automatically.
However if you change action metadata (e.g. rename or move , add parameters) - you will have to
update the action with ``st2 action update <action.ref> <action.metadata.file>```.
Alternatively, full context reload with ``st2clt reload`` will pick up all the changes.


Providing input
~~~~~~~~~~~~~~~

For a user to provide input to an ActionChain the input parameters must be defined in action metadata.

::

   ---
      # ...
      parameters:
         input1:
            type: "string"
            required: true
      # ...

The input parameter `input1` can now be referenced in the parameters field of an action element.

::

   ---
      # ...
      chain:
         -
            name: "action1"
            ref: "core.local"
            parameters:
               action1_input: "{{input1}}"
      # ...

`action1_input` has value `{{input1}}`. This syntax is variable referencing as supported
by `Jinja templating <http://jinja.pocoo.org/docs/dev/templates/>`__.
Similar constructs are also used in :doc:`Rule </rules>` criteria and action fields.

Data passing
~~~~~~~~~~~~

Similar to how input to an ActionChain can be referenced in an action elements; the output of previous action elements can also be referenced. Below is a version of the previously seen `echochain`, :github_st2:`echochain_param.yaml <contrib/examples/actions/chains/echochain_param.yaml>` with input and data passing down the flow:

.. literalinclude:: /../../contrib/examples/actions/chains/echochain_param.yaml
   :language: yaml

Details:

* Output of an action elements is always prefixed by element name. e.g. In ``{"cmd":"echo c2 {{c1.stdout}}"}`` `c1.stdout` refers to the output of 'c1' and further drills down into properties of the output.
* A special ``__results`` key provides access to the entire result upto that point of execution.

Error Reporting
~~~~~~~~~~~~~~~

ActionChain errors are classified as:

* Errors reported by a specific task in the chain. In this case the error is reported as per behavior of the particular action in the task.

Sample -

::

   "result": {
        "tasks": [
            {
                "created_at": "2015-02-27T19:29:02.057885+00:00",
                "execution_id": "54f0c57e0640fd177f278052",
                "id": "c1",
                "name": "c1",
                "result": {
                    "failed": true,
                    "return_code": 127,
                    "stderr": "bash: borg: command not found\n",
                    "stdout": "",
                    "succeeded": false
                },
                "state": "failed",
                "updated_at": "2015-02-27T19:29:03.149547+00:00",
                "workflow": null
            }
        ]
    }

* Errors experienced by the ActionChain runtime while determining the flow. In this case the error is reported as the error property of the ActionChain result.

Sample -

::

   "result": {
        "error": "Failed to run task \"c2\". Parameter rendering failed: 's1' is undefined",
        "tasks": [
            {
                "created_at": "2015-02-27T19:19:34.536558+00:00",
                "execution_id": "54f0c3460640fd15a843957d",
                "id": "c1",
                "name": "c1",
                "result": {
                    "failed": false,
                    "return_code": 0,
                    "stderr": "",
                    "stdout": "Fri Feb 27 19:19:34 UTC 2015\n",
                    "succeeded": true
                },
                "state": "succeeded",
                "updated_at": "2015-02-27T19:19:35.591297+00:00",
                "workflow": null
            }
        ],
        "traceback": "Traceback (most recent call last):..."
    }
