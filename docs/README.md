St2 Stanley
======

## Installing from packages
See [Install.md](Install.md)

## Running from sources
Install prerequisites. See Prerequisites in [main README.md](../Readme.md)

From stanley root, run make. This creates virtualenv, installs all dependencies and runs the tests.

	make all


Activate virtual environment, start and stop st2 services:

	source virtualenv/bin/activate # Activates virtual environment
	tools/lauchdev.sh start  # Launches all st2 services
	tools/lauchdev.sh stop  # Stops all st2 services

Note: If you are running from sources, anything below assumes an activated python virtualenv.

Now you can operate the system via CLI, via REST API, and via s2client Python library.

## Activate and use CLI
If installed from sources, you need to setup the CLI client into the virtualenv:

	cd st2client
	setup.py
	st2 --help

Some examples of using CLI: (See [Terminology](#Terminology) section.)

	st2 action list
	st2 run {action} {parameters}
	st2 trigger list
	st2 rule list

**TODO:**  add sample command to run action

## Terminology
1. Trigger - An external event that is mapped to a stanley input. It is the stanley invocation point.
2. Action - An activity that happens as a response to the external event.
3. Rule - A specification to invoke an "action" on a "trigger" selectively based on some criteria.
4. Sensors - An adapter to convert an external event to a form stanley understands. This is usually a piece of python code. 

## Adding a Rule
Writing a rule is a means to associate triggers to actions. Let us see an example. 

Create a rule JSON definition. See an example at [Stanley/contrib/examples/rules/sample-rule.json](../contrib/examples/rules/sample-rule.json) for the rule structure. Look at [../contrib/sandbox/packages/](../contrib/sandbox/packages/) for more sample rules.

**TODO:** draw a sample with here with comments on required and optional fields.

Deploy the rule:

	st2 rule create path/to/rule.json

## Triggers
Stanley comes bundled with two kinds of triggers viz.

1. Timers.
2. Webhooks.

Timers are used when you want to execute an action based on a schedule. Webhooks are used when you want to POST a JSON payload to an active endpoint and kickoff actions based on the payload. Note you can selectively invoke
actions by writing a suitable criteria in the rule. 

For purposes of demo, these triggers are implemented as stock sensors in the system. To see them up, look at [triggers](triggers.md) section.

## Creating custom sensors
See [sensors.md](sensors.md)

## Creating Custom Actions
See [actions.md](actions.md)

