St2 Stanley
======

## Installing from Packages
See [Install.md](install.md)

## Running from Sources

### Environment Prerequisites 

Requirements:

- git
- Python, pip, virtualenv, tox
- MongoDB -http://docs.mongodb.org/manual/installation
- Web UI
    - nodejs and npm - http://nodejs.org/
    - [bower](http://bower.io/)
    - [gulp.js](http://gulpjs.com/)

To setup the development environment from a vanilla Fedora image:

    yum install python-pip python-virtualenv python-tox gcc-c++ git-all screen
    yum install mongodb mongodb-server
    systemctl enable mongod
    systemctl start mongod
    yum install npm
    npm install -g bower
    npm install -g gulp

To setup the development environment via Vagrant:

    git clone https://github.com/StorminStanley/devenv.git
    cd devenv
    ./configure.sh dev
    vagrant up
    vagrant ssh

Please refer to the README under https://github.com/StorminStanley/devenv for additional details.

### Project Prerequisites

Once the environment is setup, clone the git repo, and make the project. This will create the python virtual environment under stanley, download and install required dependencies, and run tests.

    git clone https://github.com/StorminStanley/stanley.git
    cd stanley
    make all

### Running Stanley From Source

Create the directory /opt/stackstorm and change ownership to the user that will run the Stanley services.

    sudo mkdir -p /opt/stackstorm
    sudo chown -R OWNER:GROUP /opt/stackstorm   # Change ownership to appropriate user

To run Stanley from source, it's assumed that python virtual environment is activated and in use.

    source virtualenv/bin/activate  # Activates the python virtual environment
    tools/lauchdev.sh start         # Launches all st2 services in screen sessions
    tools/lauchdev.sh stop          # Stops all st2 screen sessions and services

If the services are started successfully, you will see the following output.

    Starting all st2 servers...
    Changing working directory to /home/vagrant/stanley...
    Starting screen session st2-datastore...
    Starting screen session st2-actionrunner...
    Starting screen session st2-action...
    Starting screen session st2-reactor...
    Starting screen session st2-reactorcontroller...
    
    There are screens on:
        7814.st2-reactorcontroller  (Detached)
        7811.st2-reactor    (Detached)
        7808.st2-action (Detached)
        7805.st2-actionrunner   (Detached)
        7802.st2-datastore  (Detached)
    5 Sockets in /var/run/screen/S-vagrant.

Stanley can now be operated using the REST API, st2 CLI, and the st2client python client library.

### Running Stanley from Packages
If you installed according to the steps at [Install.md](install.md), Stanley can be run by using the folling command:

    st2run start|stop|restart|status

### Setup st2 CLI
If installed from source, the CLI client needs to be installed into the virtualenv:

    cd stanley/st2client
    python setup.py

#### CLI Usage Examples
Please refer to the [Terminology](#Terminology) section below for definition of terms and commands.

    st2 -h
    st2 action list
    st2 run {action} {parameters}
    st2 trigger list
    st2 rule list
    st2 run local -- ls -l
    st2 run remote host='host.1, host.2' user='myuser' -- ls -l

For more details on using the CLI and python client, please visit the [client](client.md) section.

## Terminology

| Term    | Description |
|---------|-------------|
| Sensor  | An adapter to convert an external event to a form stanley understands. This is usually a piece of python code. |
| Trigger | An external event that is mapped to a stanley input. It is the stanley invocation point. |
| Rule    | A specification to invoke an "action" on a "trigger" selectively based on some criteria. |
| Action  | An activity that happens as a response to the external event. |

## Triggers
Stanley comes bundled with two kinds of triggers viz.

 - Timers
 - Webhooks

Timers are used when you want to execute an action based on a schedule. Webhooks are used when you want to POST a JSON payload to an active web endpoint and kickoff actions based on the payload. Note you can selectively invoke actions by writing a suitable criteria in the rule.

For purposes of demo, these triggers are implemented as stock sensors in the system. Please refer to the [triggers](triggers.md) section for more details on how to create and customize triggers.

## Sensors
See [sensors.md](sensors.md) for more details on how to create custom sensors.

## Rules
Writing a rule is a means to associate triggers to actions. The following is an example.

### Define a Rule in JSON
See an example at [Stanley/contrib/examples/rules/sample-rule.json](../contrib/examples/rules/sample-rule.json) for the rule structure. The directory [../contrib/sandbox/packages/](../contrib/sandbox/packages/) contains more sample rules.

The following is a sample rule structure and a listing of the required and optional elements in a Rule definition.

    {
            "name": "rule_name",                       # required
            "description": "Some test rule.",          # optional

            "trigger": {                               # required
                "name": "trigger_name"
            },

            "criteria": {                              # optional
                ...
            },

            "action": {                                # required
                "name": "action_name",
                "parameters": {                        # optional
                        ...
                }
            },

            "enabled": true                            # required
    }

## Actions
See [actions.md](actions.md) for more details on how to create custom actions.

## Storing Reusable Configuration
The datastore service allow users to store common parameters and their values as key value pairs within Stanley for reuse in sensors, actions, and rules. Please refer to the [datastore](datastore.md) section for usage.
