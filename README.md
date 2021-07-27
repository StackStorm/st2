[![StackStorm](https://github.com/stackstorm/st2/raw/master/stackstorm_logo.png)](https://www.stackstorm.com)

**StackStorm** is a platform for integration and automation across services and tools, taking actions in response to events. Learn more at [www.stackstorm.com](http://www.stackstorm.com/product).

[![Build Status](https://github.com/StackStorm/st2/actions/workflows/ci.yaml/badge.svg)](https://github.com/StackStorm/st2/actions/workflows/ci.yaml)
[![Packages Build Status](https://circleci.com/gh/StackStorm/st2/tree/master.svg?style=shield)](https://circleci.com/gh/StackStorm/st2)
[![Codecov](https://codecov.io/github/StackStorm/st2/badge.svg?branch=master&service=github)](https://codecov.io/github/StackStorm/st2?branch=master)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/1833/badge)](https://bestpractices.coreinfrastructure.org/projects/1833)
![Python 3.6,3.8](https://img.shields.io/badge/python-3.6,%203.8-blue)
[![Apache Licensed](https://img.shields.io/github/license/StackStorm/st2)](LICENSE)
[![Join our community Slack](https://img.shields.io/badge/slack-stackstorm-success.svg?logo=slack)](https://stackstorm.com/community-signup)
[![Code Search](https://img.shields.io/badge/code%20search-Sourcegraph-%2300B4F2?logo=sourcegraph)](https://sourcegraph.com/stackstorm)
[![Forum](https://img.shields.io/discourse/https/forum.stackstorm.com/posts.svg)](https://forum.stackstorm.com/)
[![Twitter Follow](https://img.shields.io/twitter/follow/StackStorm?style=social)](https://twitter.com/StackStorm/)

---

## TL;DR

* Install Get yourself a clean 64-bit Linux box that fits the [system requirements](https://docs.stackstorm.com/install/system_requirements.html). Run the installer script:

   ```bash
   curl -sSL https://stackstorm.com/packages/install.sh | bash -s -- --user=st2admin --password=Ch@ngeMe
   ```
* Read the docs: [https://docs.stackstorm.com/index.html](https://docs.stackstorm.com/install/index.html)
* Questions? Check out [forum.stackstorm.com](https://forum.stackstorm.com/)
* Or join our [Slack community](https://stackstorm.com/community-signup)

## StackStorm Overview

[![StackStorm 5 min Intro Video](https://cloud.githubusercontent.com/assets/1294734/10356016/16278d0a-6d27-11e5-987d-c8a7629a69ed.png)](https://www.youtube.com/watch?v=pzZws3ftDtA)

### About

StackStorm is a platform for integration and automation across services and tools. It ties together your existing infrastructure and application environment so you can more easily automate that environment -- with a particular focus on taking actions in response to events.

StackStorm helps automate common operational patterns. Some examples are:

* **Facilitated Troubleshooting** - triggering on system failures captured by Nagios, Sensu, New Relic and other monitoring, running a series of diagnostic checks on physical nodes, OpenStack or Amazon instances, and application components, and posting results to a shared communication context, like Slack or JIRA.
* **Automated remediation** - identifying and verifying hardware failure on OpenStack compute node, properly evacuating instances and emailing VM about potential downtime, but if anything goes wrong - freezing the workflow and calling PagerDuty to wake up a human.
* **Continuous deployment** - build and test with Jenkins, provision a new AWS cluster, turn on some traffic with the load balancer, and roll-forth or roll-back based on NewRelic app performance data.

StackStorm helps you compose these and other operational patterns as rules and workflows or actions; and these rules and workflows - the content within the StackStorm platform - are stored *as code* which means they support the same approach to collaboration that you use today for code development and can be shared with the broader open source community via [StackStorm Exchange](https://exchange.stackstorm.com).

### Who is using StackStorm?

See the list of known StackStorm [ADOPTERS.md](/ADOPTERS.md) and [Thought Leaders](https://stackstorm.com/stackstorm-thought-leaders/).

### How it works

#### StackStorm architecture

![StackStorm architecture diagram](https://user-images.githubusercontent.com/597113/92291633-6b5aae00-eece-11ea-912e-3bf977aa3cea.png)

StackStorm plugs into the environment via an extensible set of adapters: sensors and actions.

* **Sensors** are Python plugins for inbound integration that watch for events from external systems and fire a StackStorm trigger when an event happens.

* **Triggers** are StackStorm representations of external events. There are generic triggers (e.g., timers, webhooks) and integration triggers (e.g., Sensu alert, JIRA issue updated). A new trigger type can be defined by writing a sensor plugin.

* **Actions** are StackStorm outbound integrations. There are generic actions (SSH, HTTP request), integrations (OpenStack, Docker, Puppet), or custom actions. Actions are either Python plugins, or any scripts, consumed into StackStorm by adding a few lines of metadata. Actions can be invoked directly by user via CLI, API, or the web UI, or used and called as part of automations - rules and workflows.

* **Rules** map triggers to actions (or to workflows), applying matching criterias and map trigger payload data to action inputs.

* **Workflows** stitch actions together into "uber-actions", defining the order, transition conditions, and passing context data from one action to the next. Most automations are multi-step (eg: more than one action). Workflows, just like "atomic" actions, are available in the action library, and can be invoked manually or triggered by rules.

* **Packs** are the units of content deployment. They simplify the management and sharing of StackStorm pluggable content by grouping integrations (triggers and actions) and automations (rules and workflows). A growing number of packs is available on the StackStorm Exchange. Users can create their own packs,  share them on GitHub, or submit them to the StackStorm Exchange organization.

* **Audit trail** is the historical list of action executions, manual or automated, and is recorded and stored with full details of triggering context and execution results. It is is also captured in audit logs for integrating with external logging and analytical tools: LogStash, Splunk, statsd, or syslog.

StackStorm is a service with modular architecture. It is comprised of loosely coupled microservice components that communicate over a message bus, and scales horizontally to deliver automation at scale. StackStorm has a full REST API, CLI client, and web UI for admins and users to operate it locally or remotely, as well as Python client bindings for developer convenience.

StackStorm is an established project and remains actively developed by a broad community.

## Documentation

Additional documentation, including installation proceduces, action/rule/workflow authoring, and how to setup and use triggers/sensors can be found at [https://docs.stackstorm.com](https://docs.stackstorm.com).

## Hacking / Contributing

To set up a development environment and run StackStorm from sources, follow [these instructions](https://docs.stackstorm.com/development/sources.html).

For information on how to contribute, our style guide, coding conventions and more,
please visit the [Development section](https://docs.stackstorm.com/development/index.html)
in our documentation.

## Security

If you believe you found a security issue or a vulnerability, please send a description of it to
our private mailing list at info [at] stackstorm [dot] com.

Once you've submitted an issue, you should receive an acknowledgment from one our of team members
in 48 hours or less. If further action is necessary, you may receive additional follow-up emails.

For more information, please refer to https://docs.stackstorm.com/latest/security.html

## Copyright, License, and Contributor Agreement

Copyright 2020 The StackStorm Authors.
Copyright 2019 Extreme Networks, Inc.
Copyright 2014-2018 StackStorm, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this work except in compliance with the License. You may obtain a copy of the License in the [LICENSE](LICENSE) file, or at:

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

By contributing you agree that these contributions are your own (or approved by your employer) and you grant a full, complete, irrevocable copyright license to all users and developers of the project, present and future, pursuant to the license of the project.
