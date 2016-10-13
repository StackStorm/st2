[![StackStorm](https://github.com/stackstorm/st2/raw/master/stackstorm_logo.png)](http://www.stackstorm.com)

**StackStorm** is a platform for integration and automation across services and tools, taking actions in response to events. Learn more at [www.stackstorm.com](http://www.stackstorm.com/product).

[![Build Status](https://api.travis-ci.org/StackStorm/st2.svg?branch=master)](https://travis-ci.org/StackStorm/st2) [![Coverage Status](https://coveralls.io/repos/StackStorm/st2/badge.svg?branch=master&service=github)](https://coveralls.io/github/StackStorm/st2?branch=master) [![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/StackStorm/st2/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/StackStorm/st2/?branch=master) ![Python 2.7](https://img.shields.io/badge/python-2.7-blue.svg) [![Join our community Slack](https://stackstorm-community.herokuapp.com/badge.svg)](https://stackstorm.typeform.com/to/K76GRP) [![IRC](https://img.shields.io/irc/%23stackstorm.png)](http://webchat.freenode.net/?channels=stackstorm)

## StackStorm Overview
[![StackStorm 5 min Intro Video](https://cloud.githubusercontent.com/assets/1294734/10356016/16278d0a-6d27-11e5-987d-c8a7629a69ed.png)](https://www.youtube.com/watch?v=pzZws3ftDtA)
### About

StackStorm is a platform for integration and automation across services and tools. It ties together your existing infrastructure and application environment so you can more easily automate that environment -- with a particular focus on taking actions in response to events.

StackStorm helps automate common operational patterns. Some examples are:

* **Facilitated Troubleshooting** - triggering on system failures captured by Nagios, Sensu, New Relic and other monitoring, running a series of diagnostic checks on physical nodes, OpenStack or Amazon instances, and application components, and posting results to a shared communication context, like HipChat or JIRA.
* **Automated remediation** - identifying and verifying hardware failure on OpenStack compute node, properly evacuating instances and emailing VM about potential downtime, but if anything goes wrong - freezing the workflow and calling PagerDuty to wake up a human.
* **Continuous deployment** - build and test with Jenkins, provision a new AWS cluster, turn on some traffic with the load balancer, and roll-forth or roll-back based on NewRelic app performance data.

StackStorm helps you compose these and other operational patterns as rules and workflows or actions; and these rules and workflows - the content within the StackStorm platform - are stored *as code* which means they support the same approach to collaboration that you use today for code development and can be shared with the broader open source community via StackStorm.com/community for example.

### How it works

![stackstorm component diagram](https://cloud.githubusercontent.com/assets/20028/5688946/fabef9ec-9822-11e4-859e-29bbb67df85b.jpg)

    StackStorm architecture diagram

StackStorm plugs into the environment via the extensible set of adapters: sensors and actions.

* **Sensors** are python plugins for inbound integration that watch for events from external systems and fire a StackStorm trigger when event happens.

* **Triggers** are StackStorm representations of external events. There are generic triggers (e.g. timers, webhooks) and integration triggers (e.g. Sensu alert, JIRA issue updated). A new trigger type can be defined by writing a sensor plugin.

* **Actions** are StackStorm outbound integrations. There are generic actions (ssh, REST call), integrations (OpenStack, Docker, Puppet), or custom actions. Actions are either python plugins, or any scripts, consumed into StackStorm by adding a few lines of metadata. Actions can be invoked directly by user via CLI or API, or used and called as part of  automations - rules and workflows.

* **Rules** map triggers to actions (or to workflows), applying matching criterias and mapping trigger payload to action inputs.

* **Workflows** stitch actions together into “uber-actions”, defining the order, transition conditions, and passing the data. Most automations are more than one-step and thus need more than one action. Workflows, just like “atomic” actions, are available in action library, can be invoked manually or triggered by rules.

* **Packs** are the units of content deployment. They simplify the management and sharing of StackStorm pluggable content by grouping integrations (triggers and actions) and automations (rules and workflows). A growing number of packs is available on StackStorm community. User can create their own packs,  share them on Github, or submit to StackStorm community repo.

* **Audit trail** of action executions, manual or automated, is recorded and stored with full details of triggering context and execution results. It is is also captured in audit logs for integrating with external logging and analytical tools: LogStash, Splunk, statsd, syslog.

StackStorm is a service with modular architecture. It comprises loosely coupled  service components that communicate over the message bus, and scales horizontally to deliver automation at scale. StackStorm has a full REST API, CLI client for admins and users to operate it locally or remotely, and Python client bindings for developer’s convenience. Web UI is coming soon.

StackStorm is new and under active development. We are opening it early to engage community, get feedback, and refine directions, and welcome contributions.

## Documentation

Additional documentation describing installation proceduces, action/rule/workflow authoring, and how to setup and use triggers/sensors can be found at [StackStorm Docs](http://docs.stackstorm.com).

## Hacking / Contributing

To set up dev environment and run StackStorm from sources, follow [these instructions](https://docs.stackstorm.com/development/sources.html).

For information on how to contribute, style guide, coding conventions and more,
please visit the [Development section](http://docs.stackstorm.com/development/index.html)
in our documentation.

## Copyright, License, and Contributors Agreement

Copyright 2015 StackStorm, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this work except in compliance with the License. You may obtain a copy of the License in the [LICENSE](LICENSE) file, or at:

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

By contributing you agree that these contributions are your own (or approved by your employer) and you grant a full, complete, irrevocable copyright license to all users and developers of the project, present and future, pursuant to the license of the project.
