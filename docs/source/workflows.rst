Workflows
======================================

Typical datacenter operations and processes involve taking multiple actions
across various systems. To capture and automate these operations,
StackStorm uses workflows. Workflow strings atomic actions into a higher level
automation, and orchestrates their executions by calling the right action
at the right time with the right input, keeping the state, passing data,
and providing reliability and transparency to the execution.

Just like any actions, workflows are exposed in automation library,
and can be called manually, or triggered by the rules.

To create a workflow action, choose a workflow runner,
connect the actions in a workflow definition,
and provide the usual action meta data.


StackStorm offers two types of workflows - :doc:`ActionChain <actionchain>`
and :doc:`mistral`.

*   ActionChain is StackStorm's internal no-frills workflow runner.
    It provides a simple syntax to define a chain of actions,
    runs them one after another, passing data from one action to another,
    until it succeeds or fails. **Use ActionChain when you want simplicity**.

*   `Mistral <https://github.com/stackforge/mistral>`_ is a dedicated
    workflow service, integrated and bundled with StackStorm. With Mistral
    runner, you can define complex workflow logic with forks and joins,
    retry-failure policies,  delays, resumes, restarts, and manual check-points.
    **Use Mistral when you need power**.

Learn how to define and run the workflows:

.. toctree::
    :maxdepth: 1

    actionchain
    mistral

.. DZ: Deliberately commenting this out here.# .. include:: engage.rst
