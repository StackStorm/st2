CLI for Stanley
===============

### Prerequisites
The API server should be running in the background. Currently, the CLI assumes that the controllers are running on the same system.

### Installation
Activate the virtualenv, cd into st2/st2client, and run "python setup.py develop"

### Running commands
The current version of CLI supports the operations for managing trigger, action, and rule. Use help for the list of available commands. Help is generally implemented for all commands. "st2 help" returns help message for the st2 program. "st2 help command" will return the help message for the command.  "st2 command help subcommand" will return the help message for the subcommand.

### WIP
* Action Execution
* Endpoint configuration
* User authentication
* Improve ResourceManager to support advanced use cases
* Improve serialization/deserialization to support advanced use cases
* Refactoring and clean up
* Unit tests
