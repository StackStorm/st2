|StackStorm|

**StackStorm** is a platform for integration and automation across
services and tools, taking actions in response to events. Learn more at
`www.stackstorm.com`_.

|Build Status| |IRC|

StackStorm Overview
===================

About
-----

StackStorm is a platform for integration and automation across services
and tools. It ties together your existing infrastructure and application
environment so you can more easily automate that environment – with a
particular focus on taking actions in response to events.

StackStorm helps automate common operational patterns. Some examples
are:

-  **Facilitated Troubleshooting** - triggering on system failures
   captured by Nagios, Sensu, New Relic and other monitoring, running a
   series of diagnostic checks on physical nodes, OpenStack or Amazon
   instances, and application components, and posting results to a
   shared communication context, like HipChat or JIRA.
-  **Automated remediation** - identifying and verifying hardware
   failure on OpenStack compute node, properly evacuating instances and
   emailing VM about potential downtime, but if anything goes wrong -
   freezing the workflow and calling PagerDuty to wake up a human.
-  **Continuous deployment** - build and test with Jenkins, provision a
   new AWS cluster, turn on some traffic with the load balancer, and
   roll-forth or roll-back based on NewRelic app performance data.

StackStorm helps you compose these and other operational patterns as
rules and workflows or actions; and these rules and workflows - the
content within the StackStorm platform - are stored *as code* which
means they support the same approach to collaboration that you use today
for code development and can be shared with the broader open source
community via StackStorm.com/community for example.

How it works
------------

.. figure:: https://cloud.githubusercontent.com/assets/20028/5688946/fabef9ec-9822-11e4-859e-29bbb67df85b.jpg
   :alt: stackstorm component diagram

   stackstorm component diagram

::

    StackStorm architecture diagram

StackStorm plugs into the environment via the extensible set of
adapters: sensors and actions.

-  **Sensors** are python plugins for inbound integration that watch for
   events from external systems and fire a StackStorm trigger when event
   happens.

-  **Triggers** are StackStorm representations of external events. There
   are generic triggers (e.g. timers, webhooks) and integration triggers
   (e.g. Sensu alert, JIRA issue updated). A new trigger type can be
   defined by writing a sensor plugin.

-  **Actions** are StackStorm outbound integrations. There are generic
   actions (ssh, REST call), integrations (OpenStack, Docker, Puppet),
   or custom actions. Actions are either python plugins, or any scripts,
   consumed into

.. _www.stackstorm.com: http://www.stackstorm.com/product

.. |StackStorm| image:: https://github.com/stackstorm/st2/raw/master/stackstorm_logo.png
   :target: http://www.stackstorm.com
.. |Build Status| image:: https://api.travis-ci.org/StackStorm/st2.svg?branch=master
   :target: https://travis-ci.org/StackStorm/st2
.. |IRC| image:: https://img.shields.io/irc/%23stackstorm.png
   :target: http://webchat.freenode.net/?channels=stackstorm|StackStorm|

**StackStorm** is a platform for integration and automation across
services and tools, taking actions in response to events. Learn more at
`www.stackstorm.com`_.

|Build Status| |IRC|

StackStorm Overview
===================

About
-----

StackStorm is a platform for integration and automation across services
and tools. It ties together your existing infrastructure and application
environment so you can more easily automate that environment – with a
particular focus on taking actions in response to events.

StackStorm helps automate common operational patterns. Some examples
are:

-  **Facilitated Troubleshooting** - triggering on system failures
   captured by Nagios, Sensu, New Relic and other monitoring, running a
   series of diagnostic checks on physical nodes, OpenStack or Amazon
   instances, and application components, and posting results to a
   shared communication context, like HipChat or JIRA.
-  **Automated remediation** - identifying and verifying hardware
   failure on OpenStack compute node, properly evacuating instances and
   emailing VM about potential downtime, but if anything goes wrong -
   freezing the workflow and calling PagerDuty to wake up a human.
-  **Continuous deployment** - build and test with Jenkins, provision a
   new AWS cluster, turn on some traffic with the load balancer, and
   roll-forth or roll-back based on NewRelic app performance data.

StackStorm helps you compose these and other operational patterns as
rules and workflows or actions; and these rules and workflows - the
content within the StackStorm platform - are stored *as code* which
means they support the same approach to collaboration that you use today
for code development and can be shared with the broader open source
community via StackStorm.com/community for example.

How it works
------------

.. figure:: https://cloud.githubusercontent.com/assets/20028/5688946/fabef9ec-9822-11e4-859e-29bbb67df85b.jpg
   :alt: stackstorm component diagram

   stackstorm component diagram

::

    StackStorm architecture diagram

StackStorm plugs into the environment via the extensible set of
adapters: sensors and actions.

-  **Sensors** are python plugins for inbound integration that watch for
   events from external systems and fire a StackStorm trigger when event
   happens.

-  **Triggers** are StackStorm representations of external events. There
   are generic triggers (e.g. timers, webhooks) and integration triggers
   (e.g. Sensu alert, JIRA issue updated). A new trigger type can be
   defined by writing a sensor plugin.

-  **Actions** are StackStorm outbound integrations. There are generic
   actions (ssh, REST call), integrations (OpenStack, Docker, Puppet),
   or custom actions. Actions are either python plugins, or any scripts,
   consumed into

.. _www.stackstorm.com: http://www.stackstorm.com/product

.. |StackStorm| image:: https://github.com/stackstorm/st2/raw/master/stackstorm_logo.png
   :target: http://www.stackstorm.com
.. |Build Status| image:: https://api.travis-ci.org/StackStorm/st2.svg?branch=master
   :target: https://travis-ci.org/StackStorm/st2
.. |IRC| image:: https://img.shields.io/irc/%23stackstorm.png
   :target: http://webchat.freenode.net/?channels=stackstorm
