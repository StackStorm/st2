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

Some examples of using CLI:

	st2 action list
	st2 run {action} {parameters}
	st2 trigger list
	st2 rule list

**TODO:**  add sample command to run action


## Adding a Rule
Create a rule JSON definition. See an example at [Stanley/contrib/examples/rules/sample-rule.json](../contrib/examples/rules/sample-rule.json) for the rule structure. Look at [../contrib/sandbox/packages/](../contrib/sandbox/packages/) for more sample rules.

**TODO:** draw a sample with here with comments on required and optional fields.

Deploy the rule:

	st2 rule create path/to/rule.json


## Creating sensors
See [sensors.md](sensors.md)

## Creating Custom Actions
See [actions.md](actions.md)

## Creating Custom Sensors
See [sensors.md](sensors.md)

