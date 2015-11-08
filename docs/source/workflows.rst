Workflows
=========

Typical datacenter operations and processes involve taking multiple actions
across various systems. To capture and automate these operations,
|st2| uses workflows. A workflow strings atomic actions into a higher level
automation, and orchestrates their executions by calling the right action
at the right time with the right input, keeping the state, passing data,
and providing reliability and transparency to the execution.

Just like any actions, workflows are exposed in the automation library,
and can be called manually, or triggered by the rules.

To create a workflow action, choose a workflow runner,
connect the actions in a workflow definition,
and provide the usual action meta data.

|st2| supports two types of workflows - :doc:`ActionChain <actionchain>` and :doc:`Mistral <mistral>`.

*   :doc:`ActionChain <actionchain>` is |st2|'s internal no-frills workflow runner.
    It provides a simple syntax to define a chain of actions,
    runs them one after another, passing data from one action to another,
    until it succeeds or fails. **Use ActionChain when you want speed and simplicity**.

*   `Mistral :doc:`Mistral` is a dedicated
    workflow service, originated in OpenStack, integrated and bundled with |st2|. With Mistral
    runner, you can define complex workflow logic with nested workflows,
    forks, joins, and policies for error handling, retries, and delays.
    **Use Mistral when you need power and resilience**.

In addition, |st2| offers experimental support for :doc:`CloudSlang <cloudslang>` workflow.

*   `CloudSlang <http://www.cloudslang.io/>`_ is a language for defining
    workflows run by the CloudSlang Orchestration Engine. With the CloudSlang
    runner, you can define your own complex workflows or leverage the power of
    the ready-made CloudSlang `content repository <https://github.com/CloudSlang/cloud-slang-content>`_.

Learn how to define and run the workflows:

.. toctree::
    :maxdepth: 1

    actionchain
    mistral
    cloudslang

.. DZ: Deliberately commenting this out here.# .. include:: engage.rst
