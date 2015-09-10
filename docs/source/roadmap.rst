Roadmap
=======

StackStorm is new and under active development. We are opening it early to engage community, get  feedback, and refine directions, and welcome contributions. Below are key next items we see as top priorities.

* **Web UI advanced functionality:** visual workflow design representation, drag&drop workflow designer.
* **Scale improvements:** refactoring and fixes to scale out better to manage large volumes of events and actions.
* **Pack management:** Improve support for pack creation lifecycle. REST API to manage and configure packs installed in the system. Smoother integration with community content.
* **Reliability:** Focus on availability of services and improve system reliability.
* **Tags:** tag any resources, to handle actions, triggers and rules as their number grows to hundreds.
* **Action Output Structure Definition**: enable optional definition of action payload, so that it can be introspected and used when passing data between actions in worfklows.
* **Database:** move away from Mongo to Postgres and/or MySQL.
* **Pluggable runners:** We have heard that a Ruby runner would be great.
* **Datastore:**  Hierarchical, pluggable and secure datastore to bring together all the gnarly config and key spread in operations environments.
* **Bugs and smaller improvements**
* **Documentation:** generate REST API docs.
* **More integration packs:** push more content to the community to help work with most common and widely used tool. Tell us if there is tool you love and think we should integrate with or better yet write a pack yourself.
* **Various RBAC improvements** - ability to assign permissions on key value objects, ability to assign permissions on arbitrary triggers, support for a default role which is assigned to new users.
* **Advanced RBAC functionality** - ability to grant permissions on tags, RBAC for ChatOps.
* **Support for RBAC in the UI** - ability to manage and visualize RBAC assignments in the WebUI.

See :doc:`/changelog` for details on what is done.

.. rubric:: Done in TBD

* **RBAC:** Role based access control for packs, actions, triggers and rules.

.. rubric:: Done in v0.11

* **ChatOps:** two-way chat integration beyond imagination.
* **More integration packs**: Major integrations - Salt, Ansible, some significant others. `Check the full list <https://github.com/StackStorm/st2contrib/tree/master/packs>`_.

.. rubric:: Done in v0.9

* **Experimental windows support:** windows runner, and windows commands.
* **Web UI complete basics:** rule create/edit/delete in UI.

.. rubric:: Done in v0.8

* **Web UI:** refactor history view, create and edit rules and workflows, add graphical representations for workflow definitions and executions.
* **Improving** `Mistal <https://wiki.openstack.org/wiki/Mistral>`_  **integration:** simplified Mistral DSL for |st2| actions, visibility of workflow executions, and reliabile of |st2|-Mistral communication. Includes Mistral improvements, features, and fixes.
* **Operational supportability:** Better output formats, better visibility to ongoing actions, better logs, better debugging tools.
* **Scale and reliability improvements:** deployed and run at scale, shown some good numbers, and more work identified.

.. rubric:: Done in v0.6.0

* **YAML:** complete moving to YAML for defining rules, action and trigger metadata, configurations, etc.
* **Plugin isolation and management:** Improved managements of sensors, action runners and provide isolated environments.
* **Reliability:** improvements on sensor and action isolation and reliability

.. include:: engage.rst
