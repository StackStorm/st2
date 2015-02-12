Roadmap
===========

StackStorm is new and under active development. We are opening it early to engage community, get  feedback, and refine directions, and welcome contributions. Below are key next items we see as top priorities.


* **Web UI:** refactor history view, create and edit rules and workflows, add graphical representations for workflow definitions and executions.
* **Improving** `Mistal <https://wiki.openstack.org/wiki/Mistral>`_  **integration:** focus on simplifying Mistral DSL for |st2| actions, visibility of workflow executions, and reliability of |st2|-Mistral communication.
* **Operational supportability:** Better output formats, better visibility to ongoing actions, better logs, better debugging tools.
* **Pack management:** Improve support for pack creation lifecycle. REST API to manage and configure packs installed in the system. Smoother integration with community content.
* **Scale improvements:** refactoring and fixes to scale out better to manage large volumes of events and actions.
* **Reliability:** Focus on availability of services and improve system reliability. 
* **Tags:** tag any resources, to handle actions, triggers and rules as their number grows to hundreds. 
* **RBAC:** Role based access control for actions, triggers, rules, and datastore keys.
* **Database:** move away from Mongo to Postgres and/or MySQL.
* **Pluggable runners:** We have heard that a Ruby runner would be great.
* **Datastore:**  Hierarchical, pluggable and secure datastore to bring together all the gnarly config and key spread in operations environments.
* **Bugs and smaller improvements** 
* **Documentation:** generate REST API docs.
* **More integration packs:** push more content to the community to help work with most common and widely used tool. Tell us if there is tool you love and think we should integrate with or better yet write a pack yourself.

.. rubric:: Done in v0.6.0

* **YAML:** complete moving to YAML for defining rules, action and trigger metadata, configurations, etc.
* **Plugin isolation and management:** Improved managements of sensors, action runners and provide isolated environments.
* **Reliability:** improvements on sensor and action isolation and reliability

See :doc:`/changelog` for details on what is done. 


.. include:: engage.rst