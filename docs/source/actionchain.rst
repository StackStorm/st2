ActionChain
============

ActionChain is a no-frills linear workflow. On completion of a constituent action the choice between on-success and on-failure is evaluated to pick the next action. This implementation allows for passing of data between actions and finally publishes the result of each of the constituent action elements. From perspective of |st2| an ActionChain is itself an action therefore all the features of an action like execution from cli, usage in Rules etc. are automatically supported.

Authoring an ActionChain
------------------------

ActionChain's are described in json and placed inside a pack similar to other script or python actions. An ActionChain must also be associated with a metadata file that allows it to be registered as an Action by |st2| . This metadata contains name and parameter description of an action.

ActionChain metadata
~~~~~~~~~~~~~~~~~~~~

Following is sample metadata for an ActionChain named ``echochain``

.. literalinclude:: /../../contrib/examples/actions/echochain.meta.json

Note:

* `runner_type` has value `action-chain` to identify that action is an `action-chain`.
* `entry_point` links to the actual chain file relative to the location of the meta file.
* Schema followed is identical to any other action i.e. echochain is now an action in the system.

ActionChain script
~~~~~~~~~~~~~~~~~~

Following is sample script for an ActionChain named ``echochain``

.. literalinclude:: /../../contrib/examples/actions/echochain

Note:

* `chain` is the array property that contains action elements.
* Action elements are named action execution specifications. The name is scoped to an ActionChain and is used as a reference to an action element.
* `ref` property of an action element points to an Action registered in |st2| .
* `on-success` is the link to action element to invoke next on a successful execution. If not provided the ActionChain will terminate with status set to success.
* `on-failure` is the link to action element to invoke next on a failed execution. If not provided the ActionChain will terminate with the status set to error.
* `default` is the top level property that specifies start of an ActionChain.

Providing input
~~~~~~~~~~~~~~~

For a user to provide input to an ActionChain the input parameters must be defined in action metadata.

::

   {
      ...
      "parameters": {
         "input1": {
            "type": "string",
            "required": true
         }
      }
   }

The input parameter `input1` can now be referenced in the parameters field of an action element.

::

   {
      ...
      "chain": [{
         "name": "action1",
         "ref": "core.local",
         "parameters": {
            "action1_input": "{{input1}}"
         }
      }]
   }

`action1_input` has value `{{input1}}`. This syntax is variable referencing as supported by Jinja2 templating. Similar constructs are also used in `Rule </rules>`__ criteria and action fields.

Data passing
~~~~~~~~~~~~

Similar to how input to an ActionChain can be referenced in an action elements; the output of previous action elements can also be referenced. Below is a parameterized version of the previously seen `echochain`.

.. literalinclude:: /../../contrib/examples/actions/echochain_param

Note:

* Output of an action elements is always prefixed by element name. e.g. In ``{"cmd":"echo c2 {{c1.localhost.stdout}}"}`` `c1.localhost.stdout` refers to the output of 'c1' and further drills down into properties of the output.
* A special ``__results`` key provides access to the entire result upto that point of execution.
