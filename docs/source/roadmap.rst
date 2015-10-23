Roadmap
=======

StackStorm is new and under active development. We are opening it early to engage community, get feedback,  refine directions, and welcome contributions. Below are key next items we see as top priorities.

* **Complete DEB/RTM for st2 components:** Build self-sustaining RPM/DEB packages for all the StackStorm components, Mistral, Hubot and the other dependencies for a fast and reliable installation.
* **Docker based installer:** Complete the vision of OS independent, layered docker-based installer, to increase reliability, modularity, and speed of deployment.
* **Migrate away from MongoDB:** Now that the models are stable, replace Mongo, to reduce operational overhead, improve performance, and simplify licensing.
* **At-scale refinements:** Ensure event handling reliability, event storm resilience/throttling. Complete support for multi-node deployment of sensor containers and rule engines for resilience and throughput.
* **Content management, revised for multi-node deployments:** provide platform support for content deployment to worker nodes with better integration with git/GitHub, to simplify development and deployment of "automation as code" at scale.
* **Security tightening:** Complete security audit and address issues discovered so far.
* **History and Audit service:** History view with advanced search over years worth of execution records, over multiple versions of continuously upgraded StackStorm.
* **Multi target configurations for integration packs:** For a given integration pack, define and manage multiple targets - sets of configurations, so that the user can choose which one to use for a given action.
* **First class Windows support:** switch to pywinrm for better license. Remote PowerShell via Powershell.REST.API. Windows-native ActionRunners. Windows supported st2workroom.
* **Projects and Uber-flow:** introduce projects to group and manage rules and workflows. Handle versions and dependencies. "Productize" flow-rule-flow-rule chain pattern, aka "uber-flow". Manage large number of automations across users and teams, on a single StackStorm deployment at enterprise scale.
* **RBAC refinements and improvements:**

  * tag and property based filters, more refined and convenient access control
  * permissions on key value objects, arbitrary triggers, support for a default role with is assigned to new users.
  * WebUI for RBAC configuration
  * RBAC for ChatOps - allow user to authenticate with StackStorm via bot on chat and when checking permissions directly check permissions of the user who triggered an action / ran a command. Allow introduce a special set of permission types for ChatOps.
* **StackStorm Forge:** for Community and Enterprise integration and automation packs. Solve the problem of packs spread all over GitHub. Make integration and automation packs discoverable, continuously tested, and community rated
* **More integration packs:** push more content to the community to help work with most common and widely used tool. Tell us if there is tool you love and think we should integrate with or better yet write a pack yourself.
* **Action Output Structure Definition**: enable optional definition of action payload, so that it can be introspected and used when passing data between actions in workflows.
* **Datastore:**  Hierarchical, pluggable and secure datastore to bring together all the gnarly config and key spread in operations environments.
* **Documentation:** generate REST API docs.
* **Flow v2:** Visualizing workflow executions. UI improvements, including more "operator" persona features.


See :doc:`/changelog` for details on what is done.

.. rubric:: Done in v1.1

* **FLOW:** Visual workflow representation and drag-and-drop workflow designer.
* **RBAC:** Role based access control for packs, actions, triggers and rules.
* **Pluggable auth backends** including PAM, Keystone, Enterprise LDAP.
* **All-in-one installer**: production ready single-box reference deployment with graphical setup wizard.
* **RHEL 6 and 7 support**
* **Trace-tags**: ability to track a complete chain of triggers, rules, executions, related to a given triggering event.
* **Native SSH:** replace Fabric; Fabric based SSH still available and can be enabled via config.
* **WebUI major face-lift**


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
