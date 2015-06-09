|st2| Overview
====================

About
-------

|st2| is a platform for integration and automation across services and tools. It ties together your existing infrastructure and application environment so you can more easily automate that environment -- with a particular focus on taking actions in response to events.

|st2| helps automate common operational patterns. Some examples are:

* **Facilitated Troubleshooting** - triggering on system failures captured by Nagios, Sensu, New Relic and other monitoring, running a series of diagnostic checks on physical nodes, OpenStack or Amazon instances, and application components, and posting results to a shared communication context, like HipChat or JIRA.
* **Automated remediation** - identifying and verifying hardware failure on OpenStack compute node, properly evacuating instances and emailing VM about potential downtime, but if anything goes wrong - freezing the workflow and calling PagerDuty to wake up a human.
* **Continuous deployment** - build and test with Jenkins, provision a new AWS cluster, turn on some traffic with the load balancer, and roll-forth or roll-back based on NewRelic app performance data.

|st2| helps you compose these and other operational patterns as rules and workflows or actions; and these rules and workflows - the content within the |st2| platform - are stored *as code* which means they support the same approach to collaboration that you use today for code development and can be shared with the broader open source community via |st2|.com/community for example.

How it works
-------------

.. figure:: /_static/images/architecture_diagram.jpg
    :align: center

    StackStorm architecture diagram

|st2| plugs into the environment via the extensible set of adapters: sensors and actions.

* **Sensors** are python plugins for either inbound or outbound integration that receives or watches for events respectively. When an event from external systems occurs and is processed by a sensor, a |st2| trigger will be emitted into the system.

* **Triggers** are |st2| representations of external events. There are generic triggers (e.g. timers, webhooks) and integration triggers (e.g. Sensu alert, JIRA issue updated). A new trigger type can be defined by writing a sensor plugin.

* **Actions** are |st2| outbound integrations. There are generic actions (ssh, REST call), integrations (OpenStack, Docker, Puppet), or custom actions. Actions are either python plugins, or any scripts, consumed into |st2| by adding a few lines of metadata. Actions can be invoked directly by user via CLI or API, or used and called as part of  automations - rules and workflows.

* **Rules** map triggers to actions (or to workflows), applying matching criterias and mapping trigger payload to action inputs.

* **Workflows** stitch actions together into “uber-actions”, defining the order, transition conditions, and passing the data. Most automations are more than one-step and thus need more than one action. Workflows, just like “atomic” actions, are available in action library, can be invoked manually or triggered by rules.

* **Packs** are the units of content deployment. They simplify the management and sharing of |st2| pluggable content by grouping integrations (triggers and actions) and automations (rules and workflows). A growing number of packs is available on |st2| community. User can create their own packs,  share them on Github, or submit to |st2| community repo.

* **Audit trail** of action executions, manual or automated, is recorded and stored with full details of triggering context and execution results. It is is also captured in audit logs for integrating with external logging and analytical tools: LogStash, Splunk, statsd, syslog.


|st2| is a service with modular architecture. It comprises loosely coupled  service components that communicate over the message bus, and scales horizontally to deliver automation at scale. |st2| has a full REST API, CLI client for admins and users to operate it locally or remotely, and Python client bindings for developer’s convenience. Web UI is coming soon.

StackStorm is new and under active development. We are opening it early to engage community, get feedback, and refine directions, and welcome contributions.

What's Next?
-------------------------------
* Install and run - follow :doc:`/install/index`
* Learn how to use StackStorm - watch :doc:`/video`
* Build a simple automation - follow :doc:`/start` Guide
* Help us with directions - comment on the :doc:`/roadmap`
* Explore the `StackStorm community <http:://www.stackstorm.com/community/>`__


.. include:: engage.rst
